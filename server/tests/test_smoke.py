# server/tests/test_smoke.py
from sqlalchemy import text


async def test_health(client):
    """App이 TEST 안에서 실제로 응답하는지 ─ server를 띄우지 않고 부른다"""
    res = await client.get("/api/health")
    assert res.status_code == 200, res.json()


async def test_genres_are_seeded(engine):
    """결정 ②의 증거. create_all이었다면 0이 나왔을 자리이다"""
    async with engine.connect() as conn:
        count = await conn.scalar(text("SELECT count(*) FROM genres"))
    assert count == 8


async def test_leaves_a_user_behind(client):
    """다음 테스트가 확인할 '흔적'을 일부러 남긴다.
    동시에 override_get_db가 세션을 제대로 넘겨주는지도 여기서 판명난다 ─
    세션이 None이면 회원가입은 201이 아니라 500이 나온다"""
    res = await client.post(
        "/api/auth/register",
        json={
            "email": "dirty@example.com",
            "password": "testpassword123",
            "nickname": "흔적",
        },
    )
    assert res.status_code == 201, res.json()


async def test_starts_empty(engine):
    """결정 ③의 증거. 바로 앞 테스트가 사용자 1명을 남겼는데도 여기는 0이다.
    clean_tables를 지우면 이 테스트가 깨진다 ─ 그게 이 테스트가 뭔가를 지키고 있다는 뜻"""
    async with engine.connect() as conn:
        count = await conn.scalar(text("SELECT count(*) FROM users"))
    assert count == 0
