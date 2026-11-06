# app/core/oauth_state.py
"""외부 사이트(Steam · Discord)에 다녀오는 동안 "누가 보낸 손님인지"를 기억하는 서명 쪽지 (ARCHITECTURE 4.3 · 5.4절)

비유: 놀이공원 재입장 도장. 나갈 때 손등에 도장(쿠키)을 찍어 주고, 돌아오면
도장이 진짜인지 · 기한 안인지 · 이미 한 번 쓴 도장이 아닌지 보고 들여보낸다.
도장에는 "몇 번 손님이 무엇 하러 나갔는지"가 적혀 있다.

- 서명은 PyJWT로 하지만 access 토큰과 **다른 키**를 쓴다 ─ 같은 키면 state 쪽지를 출입증으로 내밀 수 있다
- 쓴 쪽지는 메모리에 적어 두고 두 번 받지 않는다. 서버 한 대 · 프로세스 하나 기준이다 (rate_limit.py와 같음, Dockerfile --workers 1)
  재시작하면 목록이 비지만, 쪽지 자체가 5분이면 끝나고 쿠키도 한 번 쓰면 지워진다
"""

import hashlib
import secrets
import time
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings

STATE_TTL_SECONDS = 5 * 60

# access 토큰 키에서 갈라 낸 키. 원래 키를 알아야만 만들 수 있고, 용도가 다르면 서로의 서명이 맞지 않는다
_STATE_KEY = hashlib.sha256(f"{settings.jwt_secret_key}|oauth-state".encode()).hexdigest()

# 쓴 nonce → 그 쪽지의 만료 시각(monotonic). 만료가 지난 것은 어차피 서명 검사에서 걸리니 버린다
_used: dict[str, float] = {}
_USED_MAX = 50_000   # 쪽지를 마구 만들어 메모리를 채우는 것도 막는다 (RateLimiter max_keys와 같은 생각)


def create_state(user_id: int, purpose: str) -> tuple[str, str]:
    """(nonce, 쿠키에 넣을 서명 쪽지)를 만든다

    nonce는 외부 사이트로 가는 주소에도 실어 보내고, 돌아올 때 쿠키 속 값과 맞춰 본다.
    purpose("steam_link" · "discord_login" ...)가 다르면 받지 않는다 ─ Steam용 도장으로 Discord 문을 열지 못하게
    """
    nonce = secrets.token_urlsafe(24)
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "nonce": nonce,
        "purpose": purpose,
        "iat": now,
        "exp": now + timedelta(seconds=STATE_TTL_SECONDS),
    }
    return nonce, jwt.encode(payload, _STATE_KEY, algorithm="HS256")


def consume_state(cookie_value: str | None, purpose: str, nonce: str | None) -> int | None:
    """쪽지를 확인하고 한 번 쓴 것으로 표시한다. 통과하면 시작한 사용자 id, 아니면 None

    실패 사유(위조 · 만료 · 재사용 · 다른 용도)를 나누지 않는다 ─ 화면에는 "다시 시도해 주세요" 하나면 된다
    """
    if not cookie_value or not nonce:
        return None
    try:
        payload = jwt.decode(
            cookie_value,
            _STATE_KEY,
            algorithms=["HS256"],
            options={"require": ["exp", "sub", "nonce", "purpose"]},
        )
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, ValueError):
        return None

    # compare_digest ─ 글자를 앞에서부터 비교하다 처음 틀린 곳에서 멈추면, 걸린 시간으로 맞은 길이를 짐작할 수 있다
    if payload["purpose"] != purpose or not secrets.compare_digest(str(payload["nonce"]), nonce):
        return None

    now = time.monotonic()
    _forget_expired(now)
    if nonce in _used:
        return None
    if len(_used) >= _USED_MAX:
        # 가득 차면 가장 오래된 것부터 버린다. 버린 쪽지도 몇 분 뒤면 서명 만료로 걸린다
        del _used[next(iter(_used))]
    _used[nonce] = now + STATE_TTL_SECONDS
    return user_id


def _forget_expired(now: float) -> None:
    # dict는 넣은 순서를 지키고, 넣을 때마다 만료가 늘 뒤로 가므로 앞에서부터만 보면 된다
    while _used:
        first = next(iter(_used))
        if _used[first] > now:
            break
        del _used[first]


def reset_used_states() -> None:
    """테스트용 ─ 앞 테스트에서 쓴 nonce가 다음 테스트에 남지 않게"""
    _used.clear()
