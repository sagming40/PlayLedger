# app/services/steam_openid.py
"""Steam 계정 연결 ─ OpenID 2.0으로 "이 Steam 계정의 주인"인지 확인한다 (decisions/0015, ARCHITECTURE 5.4절)

비유: "학번을 적어 주세요"가 아니라 "학생증을 보여 주세요".
Steam 창구(steamcommunity.com)에 가서 학생증을 확인받고 확인서를 들고 돌아온다.
확인서는 손님이 들고 오는 종이라 위조할 수 있으니, 받은 그대로 Steam에 전화해 "이거 진짜 당신이 써 준 거 맞죠?"라고 되묻는다.
"""

import re
from typing import Literal

import httpx
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

STEAM_OPENID_URL = "https://steamcommunity.com/openid/login"
OPENID_NS = "http://specs.openid.net/auth/2.0"
IDENTIFIER_SELECT = "http://specs.openid.net/auth/2.0/identifier_select"

# Steam이 돌려주는 사람 주소. 이 모양이 아니면 받지 않는다 (ARCHITECTURE 5.4절) ─ SteamID64는 17자리
CLAIMED_ID_RE = re.compile(r"https://steamcommunity\.com/openid/id/(\d{17})")

# Steam이 서명해야 하는 항목. 서명 밖의 값은 중간에서 누가 바꿔도 check_authentication이 모른다
REQUIRED_SIGNED = {"op_endpoint", "claimed_id", "identity", "return_to", "response_nonce", "assoc_handle"}

# 콜백 주소는 누구나 부를 수 있다 ─ 이상하게 큰 요청을 Steam에 그대로 넘기지 않는다
MAX_PARAMS = 30
MAX_VALUE_LENGTH = 2000

LinkResult = Literal["linked", "taken", "already", "failed"]


class SteamOpenIDUnavailable(Exception):
    """Steam에 되묻지 못했다(시간 초과 · 5xx). 위조와 구분해 "잠시 후 다시"를 보인다"""


def build_login_url(return_to: str, realm: str) -> str:
    """Steam 로그인 창구 주소. 사용자는 Steam 화면에서만 비밀번호를 친다 ─ 우리 서버는 그 값을 볼 일이 없다

    identifier_select = "어느 계정인지는 Steam에서 고르게 하라". realm은 Steam 화면에 "어느 사이트가 묻는지"로 보인다
    """
    params = {
        "openid.ns": OPENID_NS,
        "openid.mode": "checkid_setup",
        "openid.return_to": return_to,
        "openid.realm": realm,
        "openid.identity": IDENTIFIER_SELECT,
        "openid.claimed_id": IDENTIFIER_SELECT,
    }
    return str(httpx.URL(STEAM_OPENID_URL, params=params))


async def verify_assertion(
    client: httpx.AsyncClient, params: dict[str, str], expected_return_to: str
) -> str | None:
    """Steam이 들려 보낸 확인서를 검사한다. 진짜면 SteamID64, 아니면 None

    순서가 중요하다: 우리 쪽에서 볼 수 있는 것을 먼저 다 보고, 마지막에만 Steam에 전화한다
    """
    openid = {k: v for k, v in params.items() if k.startswith("openid.")}
    if len(openid) > MAX_PARAMS or any(len(v) > MAX_VALUE_LENGTH for v in openid.values()):
        return None

    if openid.get("openid.mode") != "id_res" or openid.get("openid.ns") != OPENID_NS:
        return None
    if openid.get("openid.op_endpoint") != STEAM_OPENID_URL:
        return None
    # 다른 사이트에 가라고 써 준 확인서를 우리 창구에 내미는 것을 막는다. Steam 서명은 "Steam이 썼다"까지만 보장한다
    if openid.get("openid.return_to") != expected_return_to:
        return None

    claimed_id = openid.get("openid.claimed_id", "")
    match = CLAIMED_ID_RE.fullmatch(claimed_id)
    if match is None or openid.get("openid.identity") != claimed_id:
        return None

    signed = set(openid.get("openid.signed", "").split(","))
    if not REQUIRED_SIGNED <= signed:
        return None

    # 받은 그대로 되묻는다. mode만 바꾼다 (OpenID 2.0 11.4.2절)
    try:
        res = await client.post(
            STEAM_OPENID_URL, data={**openid, "openid.mode": "check_authentication"}
        )
    except httpx.HTTPError as exc:
        raise SteamOpenIDUnavailable from exc
    if res.status_code >= 500 or res.status_code == 429:
        raise SteamOpenIDUnavailable
    if res.status_code != 200:
        return None

    # 답은 "키:값" 줄들이다. is_valid:true 한 줄이 정확히 있어야 한다 ─ 글자 포함 여부로 보면 "is_valid:true_not"도 통과한다
    lines = {
        key.strip(): value.strip()
        for key, sep, value in (line.partition(":") for line in res.text.splitlines())
        if sep
    }
    if lines.get("ns") != OPENID_NS or lines.get("is_valid") != "true":
        return None
    return match.group(1)


async def link_steam_account(db: AsyncSession, user_id: int, steam_id: str) -> LinkResult:
    """확인된 Steam ID를 이 사용자에게 붙인다

    조건부 UPDATE 한 번으로 한다 ─ "비어 있으면 채운다"를 읽고 쓰는 두 번으로 나누면,
    두 탭에서 다른 Steam으로 동시에 돌아왔을 때 뒤에 온 쪽이 앞의 것을 덮어쓴다
    다른 계정에 이미 붙은 Steam은 users.steam_id UNIQUE가 막는다 ─ 두 계정이 동시에 같은 Steam을 붙여도 하나만 남는다
    """
    try:
        updated = await db.scalar(
            update(User)
            .where(User.id == user_id, User.steam_id.is_(None))
            .values(steam_id=steam_id, steam_synced_at=None)
            .returning(User.id)
        )
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return "taken"
    if updated is not None:
        return "linked"

    # 바뀐 행이 없다 ─ 사용자가 사라졌거나(None), 이미 무언가 붙어 있다
    # 객체(db.get)가 아니라 값만 읽는다 ─ 세션에 남은 옛 객체를 돌려받으면 방금 바뀐 값을 못 본다
    current = await db.scalar(select(User.steam_id).where(User.id == user_id))
    if current is None:
        return "failed"
    return "linked" if current == steam_id else "already"


async def unlink_steam_account(db: AsyncSession, user_id: int) -> None:
    """연결을 푼다. 기록(entries)은 남긴다 (decisions/0015). 마지막 동기화 시각도 같이 비운다 (DATA_MODEL 2.1절)"""
    await db.execute(
        update(User).where(User.id == user_id).values(steam_id=None, steam_synced_at=None)
    )
    await db.commit()
