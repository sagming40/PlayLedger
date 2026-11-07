"""Steam 이름(GetPlayerSummaries) ─ 못 받아도 예외를 내지 않는다 (services/steam.py fetch_persona_name)

이름은 설정 화면에 보여 주기만 한다. 받지 못했다고 연결 · 동기화가 실패하면 안 된다
진짜 Steam은 부르지 않는다. 각 테스트가 MockTransport로 답을 정한다.
연결 · 동기화에 붙인 쪽은 test_steam_link.py · test_steam_sync.py 맨 아래
"""

import json

import httpx
import pytest

from app.services.steam import PERSONA_NAME_MAX, PLAYER_SUMMARIES_URL, fetch_persona_name

KEY = "secret-key-for-test"
STEAM_ID = "76561197960287930"
OTHER = "76561198000000001"


async def persona(respond, key: str = KEY) -> str | None:
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        return await fetch_persona_name(client, key, STEAM_ID)


def players(*items: object):
    # json.dumps(ensure_ascii=True) ─ 짝 없는 서로게이트도 "\ud800" 글자로 보낸다 (test_steam_owned.py answer와 같음)
    body = json.dumps({"response": {"players": list(items)}})
    return lambda request: httpx.Response(200, content=body, headers={"content-type": "application/json"})


async def test_parses_name_and_sends_key_in_header():
    seen: list[httpx.Request] = []

    def respond(request):
        seen.append(request)
        return players({"steamid": STEAM_ID, "personaname": "  할로우 나이트 덕후 "})(request)

    assert await persona(respond) == "할로우 나이트 덕후"
    request = seen[0]
    assert str(request.url).startswith(PLAYER_SUMMARIES_URL)
    assert request.url.params["steamids"] == STEAM_ID
    # 키는 헤더로만 ─ URL에 실리면 로그 · 예외에 찍힌다
    assert request.headers["x-webapi-key"] == KEY
    assert KEY not in str(request.url)


async def test_only_the_asked_person():
    """답에 다른 사람만 있으면 이름이 없는 것 ─ 남의 이름을 붙이지 않는다"""
    assert await persona(players({"steamid": OTHER, "personaname": "남"})) is None
    assert await persona(players({"steamid": OTHER, "personaname": "남"}, {"steamid": STEAM_ID, "personaname": "나"})) == "나"


async def test_long_name_is_cut_and_nul_removed():
    long = "가" * (PERSONA_NAME_MAX + 10)
    assert await persona(players({"steamid": STEAM_ID, "personaname": long})) == "가" * PERSONA_NAME_MAX
    assert await persona(players({"steamid": STEAM_ID, "personaname": "a\x00b"})) == "ab"


@pytest.mark.parametrize(
    "name",
    ["", "   ", "\x00", "깨진\ud800글자", 123, None],
    ids=["empty", "spaces", "nul-only", "surrogate", "number", "null"],
)
async def test_unusable_name_is_none(name):
    assert await persona(players({"steamid": STEAM_ID, "personaname": name})) is None


def steam_timeout(request):
    raise httpx.ReadTimeout("느림", request=request)


def steam_refused(request):
    raise httpx.ConnectError("거부", request=request)


@pytest.mark.parametrize(
    "respond",
    [
        steam_timeout,
        steam_refused,
        lambda r: httpx.Response(500),
        lambda r: httpx.Response(403),
        lambda r: httpx.Response(200, text="<html>점검 중</html>"),
        lambda r: httpx.Response(200, json=[]),
        lambda r: httpx.Response(200, json={"response": {}}),
        lambda r: httpx.Response(200, json={"response": {"players": {"steamid": STEAM_ID}}}),
        players("사람이 아님"),
        players(),
    ],
    ids=["timeout", "refused", "500", "403", "html", "list", "no-players", "players-dict", "player-str", "zero"],
)
async def test_failures_are_none_not_errors(respond):
    assert await persona(respond) is None


async def test_empty_key_does_not_call_steam():
    calls: list[httpx.Request] = []

    def respond(request):
        calls.append(request)
        return httpx.Response(500)

    assert await persona(respond, key="") is None
    assert calls == []
