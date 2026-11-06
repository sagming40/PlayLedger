# server/tests/conftest.py
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.oauth_state import reset_used_states
from app.core.rate_limit import ALL_LIMITERS
from app.deps import get_db, get_http_client
from app.main import app

SERVER_DIR = Path(__file__).resolve().parents[1]  # tests/ 1칸 위 = server/

# 매 test마다 비울 Table 목록
# genres는 migration이 심어준 seed이기 때문에 일부러 뺀다 ─ 비우면 장르 test를 돌리지 못한다
TABLES_TO_CLEAR = "users, refresh_tokens, games, game_genres, entries, steam_apps"


@pytest.fixture(scope="session")
def test_db_url() -> str:
    """test가 붙을 DB 주소. 안전장치를 통과한 것만 돌려준다"""
    url = settings.test_database_url
    if not url:
        pytest.exit("TEST_DATABASE_URL이 비어 있음. server/.env 확인")

    # 아래 clean_tables는 Table을 통째로 비운다
    # 이 주소가 실수로 개발 DB를 가리키면 검증용 데이터가 통째로 날아간다
    # DB 이름이 _test로 끝나지 않으면 test 자체를 시작하지 않는다
    # ⭐ 차단기는 사고가 나기 전에 달아두는 것 ⭐
    db_name = url.rsplit("/", 1)[-1]
    if not db_name.endswith("_test"):
        pytest.exit(f"TEST DB명이 _test로 끝나지 않음: {db_name}")
    return url


@pytest.fixture(scope="session", autouse=True)
def migrate(test_db_url):
    """TEST 전체에서 최초 1회 TEST DB에 migration을 전부 적용한다.

    async 함수가 아니다 (의도한) ─ alembic의 async 템플릿은 내부에서 self event loop를
    직접 연다. 이미 돌고 있는 loop 안에서 또 열게 되면 터지기 때문에, loop 밖인
    sync 함수에서 실행해야 한다. (REPL에서 block이 동작하지 않았던 것과 비슷한 종류의 함정)
    """
    cfg = Config(str(SERVER_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(SERVER_DIR / "alembic"))
    # alembic/env.py가 "비어 있을 때만 .env로 채우는" 구조라, 여기서 넣은 주소가 그대로 살아남는다
    cfg.set_main_option("sqlalchemy.url", test_db_url)
    command.upgrade(cfg, "head")


@pytest_asyncio.fixture(scope="session")
async def engine(test_db_url, migrate):   # migrate가 끝난 뒤에 엔진을 연다고 명시
    """TEST 전용 DB Engine. app/core/db.py의 개발·운영 공용 Engine과는 완전히 별개의 창고 열쇠이다"""
    eng = create_async_engine(test_db_url)
    yield eng
    await eng.dispose()


@pytest.fixture(autouse=True)
def reset_rate_limits():
    """요청 제한은 프로세스 메모리에 남는다 ─ 앞 테스트의 횟수가 다음 테스트를 막지 않게 비운다"""
    for limiter in ALL_LIMITERS:
        limiter.reset()
    # 쓴 state 목록도 프로세스 메모리에 남는다 (core/oauth_state.py)
    reset_used_states()


@pytest_asyncio.fixture(autouse=True)
async def clean_tables(engine):
    """매 TEST가 '시작하기 전에' 책상을 비운다.

    끝난 뒤가 아니라 시작 전에 비우는 이유 ─ 앞 TEST가 도중에 터져서 뒷정리를 하지 못 했더라도,
    다음 TEST는 항상 깨끗한 상태에서 시작되게 하기 위함이다.
    RESTART IDENTITY는 SERIAL 번호도 1로 되돌린다 (id가 매번 달라지면 TEST가 흔들린다)
    """
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {TABLES_TO_CLEAR} RESTART IDENTITY CASCADE"))
    yield


class FakeSteam:
    """가짜 Steam. details[appid]에 appdetails의 data를 넣어 둔다. 없으면 HTTP 500으로 답한다"""

    def __init__(self):
        self.details: dict[int, dict] = {}
        self.calls: list[int] = []
        # 이상한 응답을 재현할 때 쓴다. 넣어 두면 details보다 먼저 답한다
        self.override = None
        # Steam OpenID 되묻기(check_authentication). 받은 폼을 적어 두고 openid_answer로 답한다
        self.openid_calls: list[dict[str, str]] = []
        self.openid_answer = lambda request: httpx.Response(
            200, text="ns:http://specs.openid.net/auth/2.0\nis_valid:true\n"
        )

        # 보유 게임 목록(GetOwnedGames). owned에 게임 dict 목록을 넣어 두면 그대로 답한다. 이상한 답은 owned_answer로
        self.owned: list[dict] = []
        self.owned_calls = 0
        self.owned_answer = None

    def handle(self, request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/IPlayerService/GetOwnedGames"):
            self.owned_calls += 1
            if self.owned_answer is not None:
                return self.owned_answer(request)
            return httpx.Response(200, json={"response": {"game_count": len(self.owned), "games": self.owned}})
        if request.url.host == "steamcommunity.com":
            self.openid_calls.append(dict(httpx.QueryParams(request.content.decode())))
            return self.openid_answer(request)
        appid = int(request.url.params["appids"])
        self.calls.append(appid)
        if self.override is not None:
            return self.override(request)
        if appid not in self.details:
            return httpx.Response(500)
        return httpx.Response(200, json={str(appid): {"success": True, "data": self.details[appid]}})


@pytest.fixture
def fake_steam() -> FakeSteam:
    return FakeSteam()


@pytest_asyncio.fixture
async def client(engine, fake_steam):
    """API를 HTTP처럼 부르는 손님. 단, uvicorn을 띄우지 않고 App 객체에 직접 넣는다.
    전화로 주문하는 것이 아니라 주방에 직접 주문을 외치는 것 ─ port도 network도 사용하지 않는다"""
    TestSession = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with TestSession() as session:
            yield session

    # App이 사용하는 get_db를 TEST용으로 바꿔치기 한다
    # router·service 코드는 단 한 글자도 수정하지 않는다 ─ Depends 주입을 해둔 대가를 받는 것
    app.dependency_overrides[get_db] = override_get_db

    # 진짜 Steam을 부르지 않는다. 등록 test의 Steam 응답은 fake_steam fixture가 정한다
    # 이 override가 없으면 키 없는 CI에서 테스트가 인터넷에 나간다
    async def override_http():
        async with httpx.AsyncClient(transport=httpx.MockTransport(fake_steam.handle)) as c:
            yield c

    app.dependency_overrides[get_http_client] = override_http

    # base_url이 http가 아니라 https인 이유:
    # refresh cookie에 Secure가 붙어 있어서, http로 부르면 cookie가 아예 실리지 않는다
    # 나중에 rotation TEST를 짤 때 쿠키를 찾지 못하는 문제로 몇 시간을 날리는 문제를 사전에 방지한다
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="https://test"
    ) as ac:
        yield ac

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_http_client, None)


@pytest.fixture
def auth_headers(client):
    """계정을 하나 만들고 로그인까지 끝낸 후, 요청에 붙일 '출입증'을 돌려주는 공장

    한 테스트에서 A·B 두 계정이 필요하므로 고정값이 아닌
    '부르면 계정을 하나 만들어 주는 함수'를 반환한다.
    """

    async def _make(email: str, nickname: str = "tester") -> dict[str, str]:
        password = "testpass123"

        # ① 가입 ─ 실패하면 res.json()의 어느 fields가 왜 틀렸는지가 다 들어있다
        res = await client.post(
            "/api/auth/register",
            json={"email": email, "password": password, "nickname": nickname},
        )
        assert res.status_code == 201, res.json()

        # ② 로그인 ─ access 토큰은 응답 본문, refresh는 cookie로 온다
        res = await client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
        )
        assert res.status_code == 200, res.json()

        # ③ 출입증 형태로 가공해서 넘긴다 ─ test는 headers=에 그대로 꽂으면 끝
        token = res.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _make


@pytest_asyncio.fixture
async def session_factory(engine):
    """TEST가 직접 DB SESSION을 여는 통로

    client fixture는 '요청이 오면 FastAPI가 자동으로 SESSION을 생성하는' 구조이다
    즉, TEST가 SESSION을 손에 쥘 수 없다. 동시 실행을 TEST하려면 두 SESSION의 순서를
    TEST가 직접 지휘해야 하므로 통로를 따로 구분짓는다
    """
    return async_sessionmaker(engine, expire_on_commit=False)
