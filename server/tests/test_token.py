"""token 만료 · 재발급(rotation) · 재사용 감지

ARCHITECTURE 4.1절: refresh token을 사용할 때마다 교체되고, 폐기된 token이
다시 들어오면 그 사용자의 살아 있는 token을 전부 폐기한다
"""

from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings
from app.routers.auth import REFRESH_COOKIE_NAME

A_EMAIL = "alice@example.com"

# httpx는 base_url="https://test"의 HOST에 .local을 붙여 COOKIE를 SAVE한다
# SERVER의 DELETE 지시가 이 DOMAIN으로 나가므로, 손으로 SEED할 때도 맞춰야 한다
COOKIE_DOMAIN = "test.local"
COOKIE_PATH = "/api/auth"


def make_expired_access_token(user_id: int) -> str:
    """서명은 올바르지만 유효기간만 지난 access token

    create_access_token은 수명을 인자로 받지 않고 설정값을 읽으므로,
    설정을 건드리는 대신 여기서 직접 생성한다 (전역 상태를 오염시키지 않기 위해)
    비유: 진짜 도장이 찍힌 어제 날짜 입장권
    """
    past = datetime.now(timezone.utc) - timedelta(minutes=1)
    return jwt.encode(
        {"sub": str(user_id), "iat": past, "exp": past},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


async def test_expired_access_token_is_rejected(client, auth_headers):
    """유효기간이 지난 access token은 401. 서명이 맞아도 통과시키지 않는다"""
    await auth_headers(A_EMAIL)   # 계정 1번을 생성해 둔다

    expired = {"Authorization": f"Bearer {make_expired_access_token(1)}"}
    res = await client.get("/api/auth/me", headers=expired)
    assert res.status_code == 401, res.json()


async def test_refresh_rotates_the_cookie(client, auth_headers):
    """refresh는 새 token 한 쌍을 주고, cookie를 새 것으로 교체한다"""
    await auth_headers(A_EMAIL)

    old_cookie = client.cookies.get(REFRESH_COOKIE_NAME)
    assert old_cookie is not None, "LOGIN이 COOKIE를 SEED하지 않았다"

    res = await client.post("/api/auth/refresh")
    assert res.status_code == 200, res.json()
    assert res.json()["access_token"]

    new_cookie = client.cookies.get(REFRESH_COOKIE_NAME)
    assert new_cookie != old_cookie, "COOKIE가 교체되지 않았다"


async def test_reusing_a_revoked_token_is_detected(client, auth_headers):
    """폐기된 token이 다시 들어오면 401이고, 그 응답에서 cookie가 delete된다

    예전 세션에 겪었던 bug 자리 ─ raise 경로로 빠져나가면 cookie 삭제가 응답에 실리지 않는다
    2번째 요청의 message가 바뀌는 것이 "cookie가 실제로 지워졌다"의 증거이다
    """
    await auth_headers(A_EMAIL)

    stolen = client.cookies.get(REFRESH_COOKIE_NAME)   # 탈취했다고 가정할 token

    # 정상 rotation 1회 → stolen은 이제 폐기된 token
    res = await client.post("/api/auth/refresh")
    assert res.status_code == 200, res.json()

    # 항아리를 통째로 비우고 stolen만 SEED한다
    # 특정 COOKIE만 지우려면 DOMAIN·PATH를 정확히 알아야 하는데,
    # 이 TEST는 COOKIE가 하나뿐이라 전부 비우는 편이 단순하고 확실하다
    client.cookies.clear()
    # Attacker가 old_token을 들고 온 상황을 재현
    # PATH까지 같이 SEED해야 한다. SERVER의 DELETE 지시(path=/api/auth)가
    # PATH 없는 COOKIE는 지우지 못하기 때문 ─ COOKIE는 NAME+DOMAIN+PATH로 식별된다
    client.cookies.set(REFRESH_COOKIE_NAME, stolen, domain="test.local", path="/api/auth")
    res = await client.post("/api/auth/refresh")
    assert res.status_code == 401, res.json()
    assert res.json()["detail"] == "다시 로그인해 주세요", res.json()

    # 한 번 더 요청하면 message가 바뀌어야 한다 = cookie가 지워졌다
    res = await client.post("/api/auth/refresh")
    assert res.status_code == 401, res.json()
    assert res.json()["detail"] == "인증 정보가 없습니다", res.json()


async def test_detection_revokes_every_living_token(client, auth_headers):
    """재사용이 감지되면, rotation으로 받은 멀쩡한 token까지 함께 죽는다

    Attacker가 이미 new token을 받아갔을 수 있으므로 그것도 끊어야 한다
    """
    await auth_headers(A_EMAIL)

    stolen = client.cookies.get(REFRESH_COOKIE_NAME)

    await client.post("/api/auth/refresh")
    living = client.cookies.get(REFRESH_COOKIE_NAME)   # 지금은 유효한 token

    client.cookies.clear()
    # old_token으로 재사용 감지를 일으킨다
    client.cookies.set(REFRESH_COOKIE_NAME, stolen, domain="test.local", path="/api/auth")
    await client.post("/api/auth/refresh")

    client.cookies.clear()
    # 방금까지 멀쩡하던 token도 이제 사용하지 못한다
    client.cookies.set(REFRESH_COOKIE_NAME, living, domain="test.local", path="/api/auth")
    res = await client.post("/api/auth/refresh")
    assert res.status_code == 401, res.json()


async def test_refresh_after_logout_is_rejected(client, auth_headers):
    """LOGOUT하면 그 TOKEN은 더 이상 재발급에 사용할 수 없다"""
    await auth_headers(A_EMAIL)

    res = await client.post("/api/auth/logout")
    assert res.status_code == 204

    res = await client.post("/api/auth/refresh")
    assert res.status_code == 401, res.json()
