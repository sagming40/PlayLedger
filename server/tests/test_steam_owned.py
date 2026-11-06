"""보유 게임 목록(GetOwnedGames) ─ 비공개 프로필과 0개 구분, 이상한 응답 (ARCHITECTURE 5.1절, decisions/0016)

진짜 Steam은 부르지 않는다. 각 테스트가 MockTransport로 답을 정한다
"""

import json

import httpx
import pytest

from app.services.steam import (
    OWNED_GAMES_URL,
    OwnedGame,
    SteamProfilePrivate,
    SteamUnavailable,
    fetch_owned_games,
)

KEY = "secret-key-for-test"
STEAM_ID = "76561197960287930"


async def owned(respond) -> list[OwnedGame]:
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        return await fetch_owned_games(client, KEY, STEAM_ID)


def answer(response: object, status: int = 200):
    # json.dumps(ensure_ascii=True) ─ 짝 없는 서로게이트도 "\ud800" 글자로 보낸다. 실제 Steam JSON이 그렇게 올 수 있다
    # httpx의 json=은 UTF-8로 바꾸다가 테스트 쪽에서 먼저 터진다
    body = json.dumps({"response": response})
    return lambda request: httpx.Response(status, content=body, headers={"content-type": "application/json"})


async def test_parses_games_and_sends_key_in_header():
    seen: list[httpx.Request] = []

    def respond(request):
        seen.append(request)
        return httpx.Response(200, json={"response": {"game_count": 3, "games": [
            {"appid": 367520, "name": "Hollow Knight", "playtime_forever": 1234},
            {"appid": 570, "name": "Dota 2", "playtime_forever": 0},
            {"appid": 10, "playtime_forever": 5},   # include_appinfo가 있어도 이름이 빠질 수 있다
        ]}})

    games = await owned(respond)

    assert games == [
        OwnedGame(367520, "Hollow Knight", 1234),
        OwnedGame(570, "Dota 2", 0),
        OwnedGame(10, None, 5),
    ]
    request = seen[0]
    assert str(request.url).startswith(OWNED_GAMES_URL)
    assert request.url.params["steamid"] == STEAM_ID
    assert request.url.params["include_appinfo"] == "true"
    assert request.url.params["include_played_free_games"] == "true"
    # 키는 헤더로만 ─ URL에 실리면 로그 · 예외에 찍힌다
    assert request.headers["x-webapi-key"] == KEY
    assert KEY not in str(request.url)


async def test_private_profile_is_not_zero_games():
    """비공개는 빈 상자다. game_count가 없다"""
    with pytest.raises(SteamProfilePrivate):
        await owned(answer({}))


async def test_zero_games():
    """진짜 0개는 game_count: 0이고 games가 빠진다"""
    assert await owned(answer({"game_count": 0})) == []


async def test_bad_rows_are_skipped_not_fatal():
    games = await owned(answer({"game_count": 9, "games": [
        "not-a-dict",
        {"name": "appid 없음"},
        {"appid": "367520"},            # 문자열
        {"appid": True},                # bool은 int의 자식
        {"appid": 0},
        {"appid": 2_147_483_648},       # integer 밖
        {"appid": 1, "playtime_forever": -5},
        {"appid": 2, "playtime_forever": "12"},
        {"appid": 3, "playtime_forever": 99_999_999_999, "name": "a\ud800b"},
        {"appid": 4, "name": "  \x00  "},
    ]}))
    assert games == [
        OwnedGame(1, None, 0),
        OwnedGame(2, None, 0),
        OwnedGame(3, None, 2_147_483_647),
        OwnedGame(4, None, 0),
    ]


async def test_duplicate_appid_kept_once():
    games = await owned(answer({"game_count": 2, "games": [
        {"appid": 5, "name": "First", "playtime_forever": 10},
        {"appid": 5, "name": "Second", "playtime_forever": 99},
    ]}))
    assert games == [OwnedGame(5, "First", 10)]


def timeout(request):
    raise httpx.ReadTimeout("느림", request=request)


def refused(request):
    raise httpx.ConnectError("거부", request=request)


@pytest.mark.parametrize(
    "respond, is_timeout",
    [
        (timeout, True),
        (refused, False),
        (lambda r: httpx.Response(500), False),
        (lambda r: httpx.Response(429), False),
        (lambda r: httpx.Response(401), False),   # 우리 키 문제
        (lambda r: httpx.Response(403), False),
        (lambda r: httpx.Response(200, text="<html>점검 중</html>"), False),
        (lambda r: httpx.Response(200, json=[]), False),
        (lambda r: httpx.Response(200, json={}), False),
        (answer([]), False),
        (answer({"game_count": 1, "games": {"appid": 1}}), False),
    ],
    ids=["timeout", "refused", "500", "429", "401", "403", "html", "list", "no-response", "response-list", "games-dict"],
)
async def test_steam_failures(respond, is_timeout):
    with pytest.raises(SteamUnavailable) as caught:
        await owned(respond)
    assert caught.value.timeout is is_timeout
    # 메시지에 키 · Steam ID가 없다
    assert KEY not in str(caught.value)
    assert STEAM_ID not in str(caught.value)


async def test_empty_key_does_not_call_steam():
    calls: list[httpx.Request] = []
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: calls.append(r))) as client:
        with pytest.raises(SteamUnavailable):
            await fetch_owned_games(client, "", STEAM_ID)
    assert calls == []
