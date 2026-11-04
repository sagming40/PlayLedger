"""인증의 실패 경로 ─ 정상 경로만 있던 테스트에 빠져 있던 것들 (PLAN M4.5)

로그인 실패 문구가 갈리면 어떤 이메일이 가입됐는지 새어 나간다. 쿠키 속성은 한 글자만 빠져도 조용히 위험해진다.
"""

import asyncio
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from sqlalchemy import func, select, update

from app.core.config import settings
from app.core.security import create_access_token
from app.models.user import RefreshToken, User

EMAIL = "alice@example.com"
PASSWORD = "testpass123"
LOGIN_FAILED = "이메일 또는 비밀번호가 올바르지 않습니다"
COOKIE = "pl_refresh_token"


def body(email=EMAIL, password=PASSWORD, nickname="앨리스"):
    return {"email": email, "password": password, "nickname": nickname}


def sign(payload: dict, secret: str | None = None, algorithm: str = "HS256") -> dict:
    token = jwt.encode(payload, settings.jwt_secret_key if secret is None else secret, algorithm=algorithm)
    return {"Authorization": f"Bearer {token}"}


def future() -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=5)


# ─── 가입 ───────────────────────────────────────────────


async def test_register_never_returns_the_hash(client):
    res = await client.post("/api/auth/register", json=body())
    assert res.status_code == 201
    assert set(res.json()) >= {"id", "email", "nickname"}
    assert "password" not in res.text
    assert "hash" not in res.text


async def test_duplicate_email_is_409(client):
    assert (await client.post("/api/auth/register", json=body())).status_code == 201
    res = await client.post("/api/auth/register", json=body(nickname="다른 닉네임"))
    assert res.status_code == 409
    assert res.json()["detail"] == "이미 사용 중인 이메일입니다"


async def test_email_differing_only_in_case_is_the_same_account(client):
    assert (await client.post("/api/auth/register", json=body(email="Alice@Example.COM"))).json()["email"] == EMAIL
    assert (await client.post("/api/auth/register", json=body())).status_code == 409
    res = await client.post("/api/auth/login", json={"email": "ALICE@example.com", "password": PASSWORD})
    assert res.status_code == 200, res.text


async def test_concurrent_register_leaves_one_account(client, session_factory):
    """UNIQUE가 마지막 방어선이다 ─ 동시에 들어와도 500이 아니라 409"""
    responses = await asyncio.gather(
        client.post("/api/auth/register", json=body()),
        client.post("/api/auth/register", json=body()),
    )
    assert sorted(r.status_code for r in responses) == [201, 409]
    async with session_factory() as db:
        assert await db.scalar(select(func.count()).select_from(User)) == 1


@pytest.mark.parametrize(
    ("override", "field"),
    [
        ({"email": "not-an-email"}, "email"),
        ({"password": "short12"}, "password"),
        ({"password": "x" * 129}, "password"),
        ({"nickname": "한"}, "nickname"),
        ({"nickname": "   "}, "nickname"),
        ({"nickname": "x" * 31}, "nickname"),
    ],
)
async def test_invalid_register_is_422_on_that_field(client, override, field):
    res = await client.post("/api/auth/register", json={**body(), **override})
    assert res.status_code == 422, res.text
    assert res.json()["detail"][0]["loc"][-1] == field


# ─── 로그인 ─────────────────────────────────────────────


async def test_login_failures_are_indistinguishable(client, session_factory):
    """가입 여부 · 비밀번호 유무를 응답으로 구분할 수 없다 (DESIGN 3.1절)"""
    await client.post("/api/auth/register", json=body())
    async with session_factory() as db:
        db.add(User(email="discord@example.com", password_hash=None, nickname="디스코드"))
        await db.commit()

    attempts = [
        {"email": EMAIL, "password": "wrong-password"},
        {"email": "nobody@example.com", "password": PASSWORD},
        {"email": "discord@example.com", "password": PASSWORD},
    ]
    for attempt in attempts:
        res = await client.post("/api/auth/login", json=attempt)
        assert res.status_code == 401, res.text
        assert res.json() == {"detail": LOGIN_FAILED}
        assert COOKIE not in res.headers.get("set-cookie", "")


async def test_cookie_attributes(client):
    """속성 하나가 빠지면 조용히 위험해진다 (ARCHITECTURE 3.2절)"""
    await client.post("/api/auth/register", json=body())
    res = await client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    cookie = res.headers["set-cookie"].lower()
    assert cookie.startswith(f"{COOKIE}=")
    for attribute in ("httponly", "secure", "samesite=strict", "path=/api/auth", f"max-age={14 * 24 * 60 * 60}"):
        assert attribute in cookie, cookie
    # refresh 토큰은 본문에 없다 ─ 본문에 있으면 스크립트가 읽을 수 있다
    assert set(res.json()) == {"access_token", "token_type"}


# ─── access 토큰 ────────────────────────────────────────


async def test_me_returns_me(client, auth_headers):
    res = await client.get("/api/auth/me", headers=await auth_headers(EMAIL))
    assert res.status_code == 200
    assert res.json()["email"] == EMAIL
    assert "hash" not in res.text


async def test_me_without_token_says_bearer(client):
    res = await client.get("/api/auth/me")
    assert res.status_code == 401
    assert res.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "make_headers",
    [
        lambda: {"Authorization": "Bearer garbage"},
        lambda: {"Authorization": "Basic abc"},
        lambda: sign({"sub": "1", "exp": datetime.now(timezone.utc) - timedelta(seconds=1)}),
        lambda: sign({"sub": "1", "exp": future()}, secret="y" * 32),
        lambda: sign({"sub": "1", "exp": future()}, secret="", algorithm="none"),
        lambda: sign({"exp": future()}),
        lambda: sign({"sub": "1"}),
        lambda: sign({"sub": "abc", "exp": future()}),
        lambda: sign({"sub": "99999999999999999999", "exp": future()}),
        lambda: {"Authorization": f"Bearer {create_access_token(999_999)}"},
    ],
    ids=["garbage", "basic", "expired", "wrong-secret", "alg-none", "no-sub", "no-exp", "text-sub", "huge-sub", "no-such-user"],
)
async def test_bad_tokens_are_the_same_401(client, auth_headers, make_headers):
    await auth_headers(EMAIL)
    res = await client.get("/api/auth/me", headers=make_headers())
    assert res.status_code == 401, res.text
    assert res.json() == {"detail": "인증이 필요합니다"}


# ─── refresh ────────────────────────────────────────────


async def test_refreshed_token_really_works(client, auth_headers):
    await auth_headers(EMAIL)
    res = await client.post("/api/auth/refresh")
    assert res.status_code == 200
    me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {res.json()['access_token']}"})
    assert me.json()["email"] == EMAIL


async def test_refresh_without_cookie(client):
    res = await client.post("/api/auth/refresh")
    assert res.status_code == 401
    assert res.json() == {"detail": "인증 정보가 없습니다"}


async def test_expired_refresh_is_rejected_and_cookie_cleared(client, auth_headers, session_factory):
    await auth_headers(EMAIL)
    async with session_factory() as db:
        await db.execute(update(RefreshToken).values(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)))
        await db.commit()
    res = await client.post("/api/auth/refresh")
    assert res.status_code == 401
    assert res.json() == {"detail": "다시 로그인해 주세요"}
    assert COOKIE in res.headers["set-cookie"] and "max-age=0" in res.headers["set-cookie"].lower()


async def test_logout_is_idempotent(client, auth_headers):
    await auth_headers(EMAIL)
    assert (await client.post("/api/auth/logout")).status_code == 204
    # 쿠키 없이 또 눌러도 같다
    res = await client.post("/api/auth/logout")
    assert res.status_code == 204
    assert COOKIE in res.headers["set-cookie"]
