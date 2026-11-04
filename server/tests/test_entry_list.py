"""S-02 목록의 정렬 · 장르 필터 (REQUIREMENTS F-03, DESIGN 3.2절)."""

import pytest

A_EMAIL = "alice@example.com"
B_EMAIL = "bob@example.com"
ACTION, STRATEGY, RPG = 1, 2, 3


async def create(client, headers, title, **fields):
    res = await client.post("/api/entries", json={"title": title, "status": "PLAYING", **fields}, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


async def titles(client, headers, **params):
    res = await client.get("/api/entries", headers=headers, params=params)
    assert res.status_code == 200, res.text
    return [e["game"]["title"] for e in res.json()["items"]]


@pytest.fixture
async def seeded(client, auth_headers):
    headers = await auth_headers(A_EMAIL)
    await create(client, headers, "banana", purchased_at="2026-03-01", playtime_minutes=60, genre_ids=[ACTION])
    await create(client, headers, "Apple", purchased_at="2025-01-01", playtime_minutes=600, genre_ids=[ACTION, RPG], status="CLEARED")
    await create(client, headers, "체리", purchased_at=None, playtime_minutes=0, genre_ids=[STRATEGY], status="BACKLOG")
    await create(client, headers, "Date", purchased_at="2026-01-01", playtime_minutes=120)
    return headers


async def test_default_is_recently_updated(client, seeded):
    assert await titles(client, seeded) == ["Date", "체리", "Apple", "banana"]
    entries = (await client.get("/api/entries", headers=seeded)).json()["items"]
    banana = next(e for e in entries if e["game"]["title"] == "banana")
    await client.patch(f"/api/entries/{banana['id']}", json={"playtime_minutes": 61}, headers=seeded)
    assert (await titles(client, seeded))[0] == "banana"


async def test_sort_by_purchase_oldest_first_unknown_last(client, seeded):
    assert await titles(client, seeded, sort="purchased") == ["Apple", "Date", "banana", "체리"]


async def test_sort_by_title_ignores_case(client, seeded):
    # 대소문자를 그대로 비교하면 banana가 Date 뒤로 간다
    assert await titles(client, seeded, sort="title") == ["Apple", "banana", "Date", "체리"]


async def test_sort_by_playtime_longest_first(client, seeded):
    assert await titles(client, seeded, sort="playtime") == ["Apple", "Date", "banana", "체리"]


async def test_unknown_sort_is_422(client, seeded):
    assert (await client.get("/api/entries", headers=seeded, params={"sort": "price"})).status_code == 422


async def test_ties_do_not_repeat_across_pages(client, auth_headers):
    """값이 전부 같아도 페이지마다 겹치거나 빠지지 않는다"""
    headers = await auth_headers(A_EMAIL)
    for i in range(5):
        await create(client, headers, f"같은 값 {i}", playtime_minutes=60, purchased_at="2026-01-01")
    for sort in ("purchased", "playtime"):
        seen = []
        for offset in range(5):
            seen += await titles(client, headers, sort=sort, limit=1, offset=offset)
        assert sorted(seen) == [f"같은 값 {i}" for i in range(5)]


async def test_genre_filter(client, seeded):
    assert await titles(client, seeded, genre=ACTION, sort="title") == ["Apple", "banana"]
    res = await client.get("/api/entries", headers=seeded, params={"genre": RPG})
    assert res.json()["total"] == 1


async def test_genre_and_status_combine(client, seeded):
    assert await titles(client, seeded, genre=ACTION, status="CLEARED") == ["Apple"]
    res = await client.get("/api/entries", headers=seeded, params={"genre": STRATEGY, "status": "CLEARED"})
    assert res.json() == {"items": [], "total": 0}


async def test_game_with_many_genres_appears_once(client, seeded):
    """장르가 여러 개여도 조인으로 줄이 늘지 않는다"""
    res = await client.get("/api/entries", headers=seeded, params={"genre": RPG})
    assert [e["game"]["title"] for e in res.json()["items"]] == ["Apple"]
    assert sorted(g["id"] for g in res.json()["items"][0]["game"]["genres"]) == [ACTION, RPG]


@pytest.mark.parametrize("genre", [0, -1, 2_147_483_648, "액션"])
async def test_out_of_range_genre_is_422(client, seeded, genre):
    assert (await client.get("/api/entries", headers=seeded, params={"genre": genre})).status_code == 422


async def test_missing_genre_is_empty_list(client, seeded):
    res = await client.get("/api/entries", headers=seeded, params={"genre": 999})
    assert res.status_code == 200
    assert res.json() == {"items": [], "total": 0}


async def test_genre_filter_does_not_show_other_users(client, auth_headers, seeded):
    """게임의 장르는 공유지만 남의 기록은 나오지 않는다"""
    b = await auth_headers(B_EMAIL)
    assert await titles(client, b, genre=ACTION) == []
    await create(client, b, "다른 사람 게임", genre_ids=[ACTION])
    assert await titles(client, b, genre=ACTION) == ["다른 사람 게임"]
    assert "다른 사람 게임" not in await titles(client, seeded, genre=ACTION)
