# app/services/steam.py
"""Steam 게임 목록 미러링 · 검색 · 게임 상세 받기 (ARCHITECTURE 5.3절, decisions/0008)

비유: 서점 도매상 카탈로그를 통째로 복사해 두고(steam_apps) 우리 창고에서 찾는다.
손님이 고른 책만 도매상에 전화해서(appdetails) 표지 · 분류를 받아 온다.
"""

import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import date

import httpx
from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.normalize import normalize_title
from app.models.game import Game, Genre
from app.models.steam_app import SteamApp

APP_LIST_URL = "https://api.steampowered.com/IStoreService/GetAppList/v1/"
APP_DETAILS_URL = "https://store.steampowered.com/api/appdetails"

# 한 번에 받는 개수와 한 번에 넣는 개수는 따로 정한다
# asyncpg는 쿼리 하나에 값을 32767개까지만 받는다 (5000행 × 2컬럼 = 10000개)
PAGE_SIZE = 50_000
UPSERT_BATCH = 5_000

COVER_URL_MAX = 500   # games.cover_url 컬럼 길이와 같아야 한다 (models/game.py)
TITLE_MAX = 200       # games.title 컬럼 길이와 같아야 한다 (models/game.py)
SEARCH_LIMIT = 10


class SteamSyncError(Exception):
    """게임 목록을 받지 못했다. 메시지에 주소 · 키를 넣지 않는다"""


@dataclass
class SteamDetails:
    """appdetails에서 쓰는 값만 추린 것"""

    type: str
    name: str | None
    cover_url: str | None
    steam_genre_ids: list[str]
    released_at: date | None


# ─── 미러링 ─────────────────────────────────────────────


async def fetch_app_pages(
    client: httpx.AsyncClient, api_key: str
) -> AsyncIterator[list[dict]]:
    """게임 목록을 페이지 단위로 받는다. DLC · 소프트웨어 · 영상 · 하드웨어는 뺀다

    키는 URL이 아니라 헤더로 보낸다 ─ URL에 실으면 로그 · 예외 메시지에 그대로 찍힌다
    """
    last_appid: int | None = None
    while True:
        params: dict[str, str | int] = {
            "max_results": PAGE_SIZE,
            "include_games": "true",
            "include_dlc": "false",
            "include_software": "false",
            "include_videos": "false",
            "include_hardware": "false",
        }
        if last_appid is not None:
            params["last_appid"] = last_appid

        try:
            res = await client.get(
                APP_LIST_URL, params=params, headers={"x-webapi-key": api_key}
            )
        except httpx.HTTPError as e:
            # from None ─ 원래 예외를 이어 붙이지 않는다. 트레이스백에 요청 내용이 남지 않게
            raise SteamSyncError(f"Steam 연결 실패: {type(e).__name__}") from None

        if res.status_code != 200:
            raise SteamSyncError(f"Steam 응답 오류: HTTP {res.status_code}")

        try:
            body = res.json()["response"]
        except (ValueError, KeyError):
            raise SteamSyncError("Steam 응답 형식이 예상과 다름") from None

        yield body.get("apps", [])

        if not body.get("have_more_results"):
            return
        last_appid = body["last_appid"]


async def upsert_steam_apps(db: AsyncSession, apps: list[dict]) -> int:
    """게임 목록을 넣는다. 있으면 이름만 고치고, 지우지는 않는다 (DATA_MODEL 2.9절)

    돌려주는 값은 받은 행 중 넣을 수 있었던 개수. commit은 부르는 쪽이 한다
    """
    rows = []
    for app in apps:
        # 빈 이름은 고를 수 없다. NUL 문자는 PostgreSQL text에 넣으면 터진다
        name = (app.get("name") or "").replace("\x00", "").strip()
        if name:
            rows.append({"appid": app["appid"], "name": name})

    for start in range(0, len(rows), UPSERT_BATCH):
        stmt = insert(SteamApp).values(rows[start : start + UPSERT_BATCH])
        await db.execute(
            stmt.on_conflict_do_update(
                index_elements=[SteamApp.appid],
                set_={"name": stmt.excluded.name},
                # 이름이 그대로면 쓰지 않는다 ─ 20만 행을 매번 고치면 GIN 인덱스만 고생한다
                where=SteamApp.name != stmt.excluded.name,
            )
        )
    return len(rows)


async def sync_steam_apps(
    db: AsyncSession, client: httpx.AsyncClient, api_key: str
) -> int:
    """게임 목록 전체를 미러링한다. 페이지마다 commit한다 ─ 중간에 끊겨도 받은 만큼은 남는다"""
    if not api_key:
        raise SteamSyncError("STEAM_API_KEY가 비어 있음. server/.env 확인")

    total = 0
    async for apps in fetch_app_pages(client, api_key):
        total += await upsert_steam_apps(db, apps)
        await db.commit()
    return total


# ─── 검색 ───────────────────────────────────────────────


def _escape_like(text: str) -> str:
    """LIKE의 특수 문자를 글자 그대로 찾게 한다 ─ '%'를 쳤을 때 전부 걸리면 안 된다"""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def search_steam_apps(
    db: AsyncSession, query: str, limit: int = SEARCH_LIMIT
) -> list[SteamApp]:
    """제목에 포함되거나 비슷한 게임을 찾는다 (DESIGN 3.3절)

    ILIKE ─ "hollow"처럼 제목 일부만 친 경우
    %     ─ "hollow knigt"처럼 오타 · "baldurs gate"처럼 기호가 빠진 경우 (pg_trgm 유사도)
    둘 다 GIN 인덱스를 탄다 (DATA_MODEL 4장)
    """
    q = query.strip()
    escaped = _escape_like(q)
    stmt = (
        select(SteamApp)
        .where(
            or_(
                SteamApp.name.ilike(f"%{escaped}%", escape="\\"),
                SteamApp.name.op("%")(q),
            )
        )
        .order_by(
            # 그걸로 시작하는 제목 → 비슷한 순. 정확히 같은 제목은 유사도 1이라 저절로 맨 위다
            SteamApp.name.ilike(f"{escaped}%", escape="\\").desc(),
            func.similarity(SteamApp.name, q).desc(),
            func.length(SteamApp.name),   # 같으면 짧은 제목이 본편일 가능성이 높다
            SteamApp.appid,               # 끝까지 같으면 순서를 고정한다
        )
        .limit(limit)
    )
    result = await db.scalars(stmt)
    return list(result.all())


# ─── 게임 상세 ──────────────────────────────────────────

_KOREAN_DATE = re.compile(r"^\s*(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일\s*$")


def parse_release_date(release: object) -> date | None:
    """appdetails의 release_date를 날짜로 읽는다. 못 읽으면 None (DATA_MODEL 2.4절)

    "2017년 2월 24일"만 날짜다. 출시 전이거나 "Q1 2027" · "곧 출시"는 None이고 등록은 그대로 진행한다
    """
    if not isinstance(release, dict) or release.get("coming_soon"):
        return None
    match = _KOREAN_DATE.match(str(release.get("date", "")))
    if match is None:
        return None
    try:
        return date(int(match[1]), int(match[2]), int(match[3]))
    except ValueError:   # 2026년 2월 31일 같은 값
        return None


async def fetch_app_details(
    client: httpx.AsyncClient, appid: int
) -> SteamDetails | None:
    """고른 게임의 상세를 받는다. 어떤 이유로든 실패하면 None (예외를 내보내지 않는다)

    비공식 API라 언제든 바뀔 수 있다. 실패해도 등록은 성공해야 한다 (decisions/0008)
    DB 잠금을 잡기 전에 부를 것 ─ Steam이 느리면 그동안 다른 사용자까지 멈춘다
    """
    try:
        res = await client.get(
            APP_DETAILS_URL,
            params={
                "appids": appid,
                "l": "koreana",
                "cc": "kr",
                "filters": "basic,genres,release_date",
            },
        )
        if res.status_code != 200:
            return None
        entry = res.json()[str(appid)]
        if not entry.get("success"):
            return None
        data = entry["data"]

        cover = data.get("header_image")
        if not (isinstance(cover, str) and cover.startswith("https://") and len(cover) <= COVER_URL_MAX):
            cover = None

        name = data.get("name")
        return SteamDetails(
            type=str(data.get("type", "")),
            name=name.strip() if isinstance(name, str) else None,
            cover_url=cover,
            # Steam은 id를 문자열로 준다. genres.steam_genre_id도 문자열이다 (DATA_MODEL 2.5절)
            steam_genre_ids=[str(g["id"]) for g in data.get("genres", [])],
            released_at=parse_release_date(data.get("release_date")),
        )
    except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError):
        return None


async def game_by_appid(db: AsyncSession, appid: int) -> Game | None:
    """이미 등록된 Steam 게임을 찾는다. 외부 호출이 필요한지 판단할 때 쓴다"""
    return await db.scalar(select(Game).where(Game.steam_appid == appid))


async def mirror_name(db: AsyncSession, appid: int) -> str | None:
    """미러에 있는 게임의 이름. 없으면 None ─ 클라이언트가 보낸 appid를 믿지 않는 근거다"""
    return await db.scalar(select(SteamApp.name).where(SteamApp.appid == appid))


def usable_title(*candidates: str | None) -> str | None:
    """games.title로 쓸 수 있는 첫 후보를 고른다. 없으면 None

    앞 후보(한국어 이름)가 안 되면 다음 후보(미러 이름)를 본다
    Steam에는 414자짜리 이름도, 기호뿐인 이름도 있다 ─ 그대로 넣으면 500이 된다
    """
    for title in candidates:
        if not title or len(title.strip()) > TITLE_MAX:
            continue
        try:
            normalize_title(title)
        except ValueError:
            continue
        return title.strip()
    return None


async def genre_ids_for_steam(db: AsyncSession, steam_genre_ids: list[str]) -> list[int]:
    """Steam 장르 id를 우리 장르 id로 바꾼다. 고정 8개에 없는 인디(23) 등은 자연히 빠진다

    id 숫자는 기기마다 다르므로 steam_genre_id로 찾는다 (DATA_MODEL 2.5절)
    """
    if not steam_genre_ids:
        return []
    found = await db.scalars(
        select(Genre.id).where(Genre.steam_genre_id.in_(steam_genre_ids))
    )
    return list(found.all())
