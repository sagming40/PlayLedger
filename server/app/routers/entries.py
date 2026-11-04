# app/routers/entries.py
# 보유 기록 API ─ 등록 · 목록 · 단건 · 수정 · 삭제

from typing import Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import entry_create_limiter
from app.deps import ensure_not_limited, get_current_user, get_db, get_http_client
from app.models.entry import Entry
from app.models.game import Game
from app.models.user import User
from app.schemas.entry import (
    INT_MAX,
    EntryCreate,
    EntryListResponse,
    EntryRead,
    EntryStatus,
    EntryUpdate,
)
from app.services.entry import MAX_LIMIT, count_entries, entry_exists, get_entry, list_entries
from app.services.game import delete_owned_game, find_or_create_game
from app.services.genre import attach_genres_if_empty, genre_ids_exist, replace_genres
from app.services.steam import (
    fetch_app_details,
    game_by_appid,
    genre_ids_for_steam,
    mirror_name,
    usable_title,
)

router = APIRouter(prefix="/api/entries", tags=["entries"])

# (user_id, game_id) 복합 UNIQUE 제약의 이름 ─ Base의 naming_convention이 생성한 이름 (첫 컬럼만 들어간다)
# IntegrityError를 구분 하는데 사용한다 ('이 제약 때문에 터진 에러인지')
ENTRY_UNIQUE = "uq_entries_user_id"

# 비울 수 없는 칸의 이름 ─ 응답 문구는 화면에 그대로 보인다 (ARCHITECTURE 3.1절)
REQUIRED_FIELDS = {"status": "상태는", "playtime_minutes": "플레이타임은"}

# 한 사람의 기록 상한 ─ 공개 가입이라 요청 제한만으로는 표가 끝없이 커질 수 있다 (decisions/0011)
# 정확한 잠금은 걸지 않는다. 동시 요청으로 몇 개 넘쳐도 문제가 없는 값이다
MAX_ENTRIES_PER_USER = 5000


async def _get_my_entry_or_404(
    db: AsyncSession, *, user_id: int, entry_id: int, for_update: bool = False
) -> Entry:
    """내 보유 기록을 꺼낸다. 없거나 다른 유저의 것이면 404

    단건 · 수정 · 삭제 3곳이 같은 상태 코드 · 같은 문구를 써야 한다
    한 곳만 문구가 바뀌면 '없는 것'과 '남의 것'의 응답이 갈려 존재 여부가 새어 나간다
    """
    # integer 범위를 넘는 id는 DB에 묻기도 전에 asyncpg가 터진다(500) ─ 그런 기록은 있을 수 없으니 없는 것과 같이 404
    # 422로 돌려주면 '없는 id'와 응답이 갈린다. 주소창에 아무 숫자나 쳐 볼 수 있는 곳이다 (S-04 /library/:id)
    entry = None
    if 1 <= entry_id <= INT_MAX:
        entry = await get_entry(db, user_id=user_id, entry_id=entry_id, for_update=for_update)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="기록을 찾을 수 없습니다",
        )
    return entry


async def _ensure_genres_exist(db: AsyncSession, genre_ids: list[int]) -> None:
    """없는 장르 id가 섞여 있으면 422로 거절한다 (등록 · 수정 공통)"""
    if not await genre_ids_exist(db, genre_ids):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="존재하지 않는 장르가 포함되어 있습니다",
        )


def _already_registered() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="이미 등록된 게임입니다",
    )


def _steam_rejected(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)


async def _steam_game(
    db: AsyncSession,
    http: httpx.AsyncClient,
    user_id: int,
    appid: int,
    genre_ids: list[int],
) -> tuple[Game, list[int]]:
    """Steam에서 고른 게임을 얻고, 연결할 장르를 정한다 (ARCHITECTURE 5.3절)

    외부 호출은 잠금을 잡기 전인 여기서 끝낸다. 장르 잠금은 이 함수가 끝난 뒤에 걸린다
    """
    # 클라이언트가 보낸 번호를 믿지 않는다 ─ 미러에 없는 번호로 공유 테이블에 가짜 게임을 만들 수 없게
    name = await mirror_name(db, appid)
    if name is None:
        raise _steam_rejected("Steam 게임 목록에 없는 게임입니다")

    game = await game_by_appid(db, appid)

    # 이미 내 것이면 Steam을 부를 필요도 없이 거절한다
    if game is not None and await entry_exists(db, user_id=user_id, game_id=game.id):
        raise _already_registered()

    # 처음 들어오는 게임이거나, 지난번에 Steam이 실패해 커버가 빈 게임만 부른다
    details = None
    if game is None or game.cover_url is None:
        # 외부 호출 동안 DB 연결을 붙들지 않는다 ─ Steam이 느릴 때 연결 풀이 말라 다른 요청까지 멈춘다
        # 아직 쓴 것이 없어 읽기 트랜잭션만 닫힌다. expire_on_commit=False라 읽어 둔 객체는 그대로 쓸 수 있다
        await db.commit()
        details = await fetch_app_details(http, appid)

    if details is not None and details.type != "game":
        raise _steam_rejected("게임이 아닌 항목은 등록할 수 없습니다")

    if game is None:
        title = usable_title(details.name if details else None, name)
        if title is None:
            raise _steam_rejected("이 게임은 이름을 쓸 수 없어요. 제목을 직접 입력해 주세요")
    else:
        title = game.title   # 먼저 등록한 사람의 제목이 유지된다

    game = await find_or_create_game(
        db,
        title,
        appid,
        released_at=details.released_at if details else None,
        cover_url=details.cover_url if details else None,
    )

    # Steam 장르가 있으면 그것을, 고정 8개와 겹치지 않으면 사용자가 고른 값을 쓴다 (DATA_MODEL 2.5절)
    steam_ids = await genre_ids_for_steam(db, details.steam_genre_ids) if details else []
    return game, steam_ids or genre_ids


# 장르 목록과 달리 라우터 전체에 거는 대신 매개변수로 받는다
# Why? "로그인했는가"뿐만 아니라 "누구인가(user.id)"도 필요하기 때문
# status_code=201 = "새로 만들어졌다" (상태 코드 200 응답은 "성공"이라는 뜻이다)
@router.post("", response_model=EntryRead, status_code=status.HTTP_201_CREATED)
async def create_entry(
    data: EntryCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    http: httpx.AsyncClient = Depends(get_http_client),
) -> Entry:
    """보유 기록을 등록한다. (게임이 없으면 게임도 함께 등록)

    비유: 도서관 대출 기록 적기. 책(게임) 자체가 서가에 없으면 먼저 들여놓은 후
    그 책에 내 이름이 적힌 대출 기록(보유 기록)을 적는다
    """
    ensure_not_limited(entry_create_limiter, str(user.id))
    entry_create_limiter.hit(str(user.id))

    if await count_entries(db, user.id) >= MAX_ENTRIES_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"기록은 최대 {MAX_ENTRIES_PER_USER:,}개까지 등록할 수 있습니다",
        )

    # ① 없는 장르 id가 섞여 있으면 거절 ─ 게임 상태와 상관없이 항상 검사
    await _ensure_genres_exist(db, data.genre_ids)

    # ② 게임 찾기/만들기 ─ 판별은 서비스 한 곳에서만 (DATA_MODEL 2.4절)
    genre_ids = data.genre_ids
    if data.steam_appid is not None:
        game, genre_ids = await _steam_game(db, http, user.id, data.steam_appid, data.genre_ids)
    else:
        game = await find_or_create_game(db, data.title, owner_user_id=user.id)

    # ③ 이미 내 라이브러리에 있으면 거절 (DESIGN 3.3절 문구)
    if await entry_exists(db, user_id=user.id, game_id=game.id):
        raise _already_registered()

    # ④ 장르가 빈 게임만 채운다 (DATA_MODEL 2.5절) ─ 직접 등록한 게임은 여기까지 왔으면 새 게임이다
    await attach_genres_if_empty(db, game.id, genre_ids)

    # ⑤ 보유 기록 만들기
    # model_dump = schema를 Dictionary로 펼친다. title · genre_ids는 entries의 column이 아니라 제외
    # user_id · game_id · source는 요청이 아니라 server가 채운다 (client를 신뢰하지 않는다)
    # Steam에서 고른 게임도 source는 MANUAL이다 ─ STEAM이면 M8 동기화가 입력한 플레이타임을 덮어쓴다 (ARCHITECTURE 5.3절)
    entry = Entry(
        user_id=user.id,
        game_id=game.id,
        source="MANUAL",
        **data.model_dump(exclude={"title", "steam_appid", "genre_ids"}),
    )
    db.add(entry)

    try:
        await db.commit()
    except IntegrityError as e:
        # ③과 commit 사이에 동일 유저의 동일 게임 요청이 먼저 종료된 경우 (2차 방어)
        # 회원가입의 이메일 중복 처리와 같은 구조
        await db.rollback()
        if ENTRY_UNIQUE in str(e.orig):
            raise _already_registered()
        raise   # 예상치 못 한 제약 위반은 숨기지 않고 그대로 터뜨린다

    # ⑥ 응답용 게임 · 장르까지 다시 불러온다
    # entry.id는 commit(내부적으로 flush) 시에 DB가 채웠고
    # expire_on_commit=False로 설정했기 때문에 그대로 읽힌다
    return await get_entry(db, user_id=user.id, entry_id=entry.id)


@router.get("", response_model=EntryListResponse)
async def list_my_entries(
    # Query(...) = 주소 뒤 ?status=BACKLOG&limit=20 부분을 받는다
    # ge/le로 범위를 강제한다 ─ limit=0이나 음수 offset은 상태 코드 422
    status_filter: EntryStatus | None = Query(default=None, alias="status"),
    # 없는 장르 id는 에러가 아니라 빈 목록이다 ─ 찾는 조건에 맞는 게임이 없을 뿐이다
    genre: int | None = Query(default=None, ge=1, le=INT_MAX),
    sort: Literal["updated", "purchased", "title", "playtime"] = "updated",
    limit: int = Query(default=20, ge=1, le=MAX_LIMIT),
    # 상한이 없으면 PostgreSQL bigint를 넘는 값에서 500이 난다. 기록 수가 integer를 넘을 일은 없다
    offset: int = Query(default=0, ge=0, le=INT_MAX),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EntryListResponse:
    """내 보유 기록 목록. (S-02 라이브러리)

    alias="status"를 사용한 이유: 주소에는 ?status=로 받되,
    함수 안에서는 fastapi의 status 모듈과 이름이 겹치지 않게 status_filter로 부른다
    """
    items, total = await list_entries(
        db, user_id=user.id, status=status_filter, genre_id=genre, sort=sort, limit=limit, offset=offset
    )
    return EntryListResponse(items=items, total=total)


# {entry_id} = 주소의 그 자리 값을 함수 인자로 받는다 (/api/entries/7 → entry_id=7)
@router.get("/{entry_id}", response_model=EntryRead)
async def get_my_entry(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Entry:
    """내 보유 기록 하나. (S-04 상세)

    다른 유저의 기록이면 403이 아니라 404
    ─ 403은 "그 기록이 존재한다"라는 걸 알려주는 셈이다
    """
    return await _get_my_entry_or_404(db, user_id=user.id, entry_id=entry_id)


@router.patch("/{entry_id}", response_model=EntryRead)
async def update_my_entry(
    entry_id: int,
    data: EntryUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Entry:
    """내 보유 기록을 수정한다. 보낸 항목만 바꾼다. (S-03 수정 모드)

    PATCH = 일부만 수정. (PUT = "통째로 교체" ─ 보내지 않은 항목도 지워진다)
    """
    # 잠그고 읽는다 ─ 안 잠그면 읽은 뒤 다른 기기가 지웠을 때 UPDATE가 0행이 되어 StaleDataError(500)가 난다
    # 잠그면 삭제가 이 수정이 끝나기를 기다리고, 먼저 지워졌으면 여기서 404가 난다
    entry = await _get_my_entry_or_404(db, user_id=user.id, entry_id=entry_id, for_update=True)

    # exclude_unset=True = 요청에 '실제로 적어 보낸' 항목만 꺼낸다
    # True로 설정하지 않으면 보내지 않은 항목까지 None으로 채워져 멀쩡한 값이 지워진다
    changes = data.model_dump(exclude_unset=True)

    # 장르는 따로 처리한다 ─ 장르는 entries의 column이 아닌 game에 붙는다
    # pop = 꺼내면서 목록에서 제외시키기. 남은 변경은 전부 entries의 컬럼이 된다
    genre_ids = changes.pop("genre_ids", None)

    # NOT NULL 컬럼에 null을 보낸 경우를 막는다
    # schema의 None은 "보내지 않음"이라는 뜻이라, 여기까지 None으로 들어왔다면
    # 유저가 명시적으로 null을 적어 보냈다는 뜻 → DB에 넣으면 500이므로 422로 거부
    for field, label in REQUIRED_FIELDS.items():
        if field in changes and changes[field] is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"{label} 비울 수 없습니다",
            )

    # 장르를 보냈으면 연결 규칙을 그대로 적용 (DATA_MODEL 2.5절)
    # 내가 직접 등록한 게임은 통째로 바꾼다
    # Steam 게임은 0개인 경우에만 채워지고, 이미 존재하는 경우 조용히 무시된다
    if genre_ids is not None:
        await _ensure_genres_exist(db, genre_ids)
        if entry.game.owner_user_id == user.id:
            await replace_genres(db, entry.game_id, genre_ids)
            # 장르만 바꾸면 entries 행이 그대로라 onupdate가 돌지 않는다 ─ 최근 수정순 맨 위로 올라와야 한다
            entry.updated_at = func.now()
        else:
            await attach_genres_if_empty(db, entry.game_id, genre_ids)

    # setattr(객체, "이름", 값) = "객체.이름 = 값"과 같다
    # 변경할 항목이 그때그때 다르므로 이름을 String으로 받아 넣는다
    for field, value in changes.items():
        setattr(entry, field, value)

    # updated_at은 모델의 onupdate가 갱신한다 ─ 건드리지 않는다
    await db.commit()
    # commit으로 잠금이 풀린 직후 기다리던 삭제가 먼저 끝날 수 있다 ─ None을 응답 모델에 넘기면 500이므로 같은 404로
    return await _get_my_entry_or_404(db, user_id=user.id, entry_id=entry_id)


# status_code=204 ─ "요청 성공. 반환할 내용 없음." (응답 본문 없음)
# 삭제된 것을 응답에 담아봐야 이미 사라진 값이라 의미가 없다
@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_entry(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """내 보유 기록을 삭제한다 (S-04의 ⋮ 메뉴)

    Steam 게임은 지우지 않는다 ─ 다른 유저가 사용하고 있는 공유 데이터이다.
    비유: 도서관 대출 카드만 버리고 책은 서가에 그대로 둔다
    직접 등록한 게임은 나만 쓰므로 함께 지운다 ─ 개인 서가의 책까지 치운다 (decisions/0011)
    """
    # 잠근다 ─ 두 탭이 동시에 지우면 늦은 쪽은 404. 잠금 순서는 수정과 같다(기록 → 게임)
    entry = await _get_my_entry_or_404(db, user_id=user.id, entry_id=entry_id, for_update=True)
    game_id = entry.game_id

    await db.delete(entry)
    # entries.game_id가 RESTRICT라 기록이 먼저 DB에서 지워져야 게임을 지울 수 있다
    await db.flush()
    await delete_owned_game(db, game_id, owner_user_id=user.id)
    await db.commit()
    # 204는 본문이 없어야 하므로 아무것도 반환하지 않는다
