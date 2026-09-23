# app/routers/entries.py
# 보유 기록 API ─ 등록 · 목록 · 단건 · 수정 · 삭제

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.models.entry import Entry
from app.models.user import User
from app.schemas.entry import EntryCreate, EntryRead
from app.services.entry import entry_exists, get_entry
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
