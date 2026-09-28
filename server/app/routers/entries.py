# app/routers/entries.py
# 보유 기록 API ─ 등록 · 목록 · 단건 · 수정 · 삭제

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.models.entry import Entry
from app.models.user import User
from app.schemas.entry import (
    EntryCreate,
    EntryListResponse,
    EntryRead,
    EntryStatus,
    EntryUpdate,
)
from app.services.entry import MAX_LIMIT, entry_exists, get_entry, list_entries
from app.services.game import find_or_create_game
from app.services.genre import attach_genres_if_empty, genre_ids_exist

router = APIRouter(prefix="/api/entries", tags=["entries"])

# (user_id, game_id) 복합 UNIQUE 제약의 이름 ─ Base의 naming_convention이 생성한 이름
# IntegrityError를 구분 하는데 사용한다 ('이 제약 때문에 터진 에러인지')
ENTRY_UNIQUE = "uq_entries_user_id_game_id"


# 장르 목록과 달리 라우터 전체에 거는 대신 매개변수로 받는다
# Why? "로그인했는가"뿐만 아니라 "누구인가(user.id)"도 필요하기 때문
# status_code=201 = "새로 만들어졌다" (상태 코드 200 응답은 "성공"이라는 뜻이다)
@router.post("", response_model=EntryRead, status_code=status.HTTP_201_CREATED)
async def create_entry(
    data: EntryCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Entry:
    """보유 기록을 등록한다. (게임이 없으면 게임도 함께 등록)

    비유: 도서관 대출 기록 적기. 책(게임) 자체가 서가에 없으면 먼저 들여놓은 후
    그 책에 내 이름이 적힌 대출 기록(보유 기록)을 적는다
    """
    # ① 없는 장르 id가 섞여 있으면 거절 ─ 게임 상태와 상관없이 항상 검사
    if not await genre_ids_exist(db, data.genre_ids):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="존재하지 않는 장르가 포함되어 있습니다",
        )

    # ② 게임 찾기/만들기 ─ 판별은 서비스 한 곳에서만 (ERD 2.4절)
    game = await find_or_create_game(db, data.title)

    # ③ 이미 내 라이브러리에 있으면 거절 (UI_DESIGN 3.3절 문구)
    if await entry_exists(db, user_id=user.id, game_id=game.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 등록된 게임입니다",
        )

    # ④ 장르가 빈 게임만 채운다 (ERD 2.5절)
    await attach_genres_if_empty(db, game.id, data.genre_ids)

    # ⑤ 보유 기록 만들기
    # model_dump = schema를 Dictionary로 펼친다. title · genre_ids는 entries의 column이 아니라 제외
    # user_id · game_id · source는 요청이 아니라 server가 채운다 (client를 신뢰하지 않는다)
    entry = Entry(
        user_id=user.id,
        game_id=game.id,
        source="MANUAL",
        **data.model_dump(exclude={"title", "genre_ids"}),
    )
    db.add(entry)

    try:
        await db.commit()
    except IntegrityError as e:
        # ③과 commit 사이에 동일 유저의 동일 게임 요청이 먼저 종료된 경우 (2차 방어)
        # 회원가입의 이메일 중복 처리와 같은 구조
        await db.rollback()
        if ENTRY_UNIQUE in str(e.orig):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 등록된 게임입니다",
            )
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
    limit: int = Query(default=20, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EntryListResponse:
    """내 보유 기록 목록. (S-02 라이브러리)

    alias="status"를 사용한 이유: 주소에는 ?status=로 받되,
    함수 안에서는 fastapi의 status 모듈과 이름이 겹치지 않게 status_filter로 부른다
    """
    items, total = await list_entries(
        db, user_id=user.id, status=status_filter, limit=limit, offset=offset
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
    entry = await get_entry(db, user_id=user.id, entry_id=entry_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="기록을 찾을 수 없습니다",
        )
    return entry


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
    entry = await get_entry(db, user_id=user.id, entry_id=entry_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="기록을 찾을 수 없습니다",
        )

    # exclude_unset=True = 요청에 '실제로 적어 보낸' 항목만 꺼낸다
    # True로 설정하지 않으면 보내지 않은 항목까지 None으로 채워져 멀쩡한 값이 지워진다
    changes = data.model_dump(exclude_unset=True)

    # 장르는 따로 처리한다 ─ 장르는 entries의 column이 아닌 game에 붙는다
    # pop = 꺼내면서 목록에서 제외시키기. 남은 변경은 전부 entries의 컬럼이 된다
    genre_ids = changes.pop("genre_ids", None)

    # NOT NULL 컬럼에 null을 보낸 경우를 막는다
    # schema의 None은 "보내지 않음"이라는 뜻이라, 여기까지 None으로 들어왔다면
    # 유저가 명시적으로 null을 적어 보냈다는 뜻 → DB에 넣으면 500이므로 422로 거부
    for field in ("status", "playtime_minutes"):
        if field in changes and changes[field] is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{field}은(는) 비울 수 없습니다",
            )

    # 장르를 보냈으면 연결 규칙을 그대로 적용 (ERD 2.5절)
    # 0개인 게임에만 채워지고, 이미 존재하는 경우 조용히 무시된다
    if genre_ids is not None:
        if not await genre_ids_exist(db, genre_ids):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="존재하지 않는 장르가 포함되어 있습니다",
            )
        await attach_genres_if_empty(db, entry.game_id, genre_ids)

    # setattr(객체, "이름", 값) = "객체.이름 = 값"과 같다
    # 변경할 항목이 그때그때 다르므로 이름을 String으로 받아 넣는다
    for field, value in changes.items():
        setattr(entry, field, value)

    # updated_at은 모델의 onupdate가 갱신한다 ─ 건드리지 않는다
    await db.commit()
    return await get_entry(db, user_id=user.id, entry_id=entry_id)


# status_code=204 ─ "요청 성공. 반환할 내용 없음." (응답 본문 없음)
# 삭제된 것을 응답에 담아봐야 이미 사라진 값이라 의미가 없다
@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_entry(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """내 보유 기록을 삭제한다 (S-04의 ⋮ 메뉴)

    게임(games)은 지우지 않는다 ─ 다른 유저가 사용하고 있는 공유 데이터이다.
    비유: 도서관 대출 카드만 버리고 책은 서가에 그대로 둔다
    """
    entry = await get_entry(db, user_id=user.id, entry_id=entry_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="기록을 찾을 수 없습니다",
        )

    await db.delete(entry)
    await db.commit()
    # 204는 본문이 없어야 하므로 아무것도 반환하지 않는다
