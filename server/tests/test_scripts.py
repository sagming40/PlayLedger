"""손으로 돌리는 스크립트 ─ 운영에 들어갈 때 처음 도는 코드라 터지면 곤란하다 (PLAN M4.5)"""

import httpx
import pytest
from sqlalchemy import func, select

from app.models.entry import Entry
from app.models.steam_app import SteamApp
from app.models.user import User
from app.scripts import seed_demo, sync_steam_apps

KEY = "secret-key-for-test"


class NoDispose:
    """스크립트 끝의 engine.dispose()가 테스트의 엔진을 건드리지 않게"""

    async def dispose(self):
        return None


@pytest.fixture
def seed_env(monkeypatch, session_factory):
    monkeypatch.setattr(seed_demo, "AsyncSessionLocal", session_factory)
    monkeypatch.setattr(seed_demo, "engine", NoDispose())
    monkeypatch.setattr(seed_demo.settings, "database_url", "postgresql+asyncpg://u:p@localhost:5434/x")


@pytest.fixture
def sync_env(monkeypatch, session_factory):
    monkeypatch.setattr(sync_steam_apps, "AsyncSessionLocal", session_factory)
    monkeypatch.setattr(sync_steam_apps, "engine", NoDispose())
    monkeypatch.setattr(sync_steam_apps.settings, "steam_api_key", KEY)

    def use(respond):
        real = httpx.AsyncClient
        monkeypatch.setattr(
            sync_steam_apps.httpx,
            "AsyncClient",
            lambda timeout: real(transport=httpx.MockTransport(respond), timeout=timeout),
        )

    return use


async def make_user(session_factory, email="me@example.com") -> int:
    async with session_factory() as db:
        user = User(email=email, password_hash="x", nickname="나")
        db.add(user)
        await db.commit()
        return user.id


async def count_entries(session_factory) -> int:
    async with session_factory() as db:
        return await db.scalar(select(func.count()).select_from(Entry))


async def test_seed_fills_an_empty_account(seed_env, session_factory, capsys):
    await make_user(session_factory)
    # 이메일은 가입 때처럼 소문자로 맞춰 찾는다
    assert await seed_demo.main("ME@example.com") == 0
    assert await count_entries(session_factory) == len(seed_demo.DEMO)
    assert f"{len(seed_demo.DEMO)}개" in capsys.readouterr().out


async def test_seed_refuses_unknown_account(seed_env, session_factory, capsys):
    assert await seed_demo.main("nobody@example.com") == 1
    assert "실패" in capsys.readouterr().err


async def test_seed_refuses_account_with_entries(seed_env, session_factory, capsys):
    await make_user(session_factory)
    assert await seed_demo.main("me@example.com") == 0
    assert await seed_demo.main("me@example.com") == 1
    assert await count_entries(session_factory) == len(seed_demo.DEMO)


async def test_seed_refuses_remote_database(seed_env, session_factory, monkeypatch, capsys):
    await make_user(session_factory)
    monkeypatch.setattr(seed_demo.settings, "database_url", "postgresql+asyncpg://u:p@db.example.com/x")
    assert await seed_demo.main("me@example.com") == 1
    assert await count_entries(session_factory) == 0
    # 운영 DB 주소의 비밀번호를 찍지 않는다
    assert "u:p" not in capsys.readouterr().err


async def test_sync_reports_rows(sync_env, session_factory, capsys):
    sync_env(lambda r: httpx.Response(200, json={"response": {"apps": [{"appid": 1, "name": "a"}], "have_more_results": False}}))
    assert await sync_steam_apps.main() == 0
    assert "1건" in capsys.readouterr().out
    async with session_factory() as db:
        assert await db.scalar(select(func.count()).select_from(SteamApp)) == 1


async def test_sync_failure_exits_1_without_the_key(sync_env, capsys):
    sync_env(lambda r: httpx.Response(403))
    assert await sync_steam_apps.main() == 1
    captured = capsys.readouterr()
    assert "실패" in captured.err
    assert KEY not in captured.err + captured.out


async def test_sync_without_key_exits_1(sync_env, monkeypatch, capsys):
    monkeypatch.setattr(sync_steam_apps.settings, "steam_api_key", "")
    assert await sync_steam_apps.main() == 1
    assert "STEAM_API_KEY" in capsys.readouterr().err
