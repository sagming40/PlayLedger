"""보유 기록 API의 경계값 ─ 잘못된 입력은 전부 422/404이고 500이 없다 (PLAN M4.5)"""

import pytest

from app.schemas.entry import INT_MAX

A = "a@example.com"
B = "b@example.com"


async def entry_of(client, headers, **fields):
    res = await client.post("/api/entries", json={"title": "Celeste", **fields}, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


# ─── 등록 ───────────────────────────────────────────────


@pytest.mark.parametrize(
    "bad",
    [
        {},
        {"title": "Celeste", "steam_appid": 1},
        {"title": "!!!"},
        {"title": "   "},
        {"title": "x" * 201},
        {"title": "Celeste", "source": "STEAM"},
        {"title": "Celeste", "status": "UNKNOWN"},
        {"title": "Celeste", "genre_ids": [999]},
        {"title": "Celeste", "genre_ids": [0]},
        {"title": "Celeste", "genre_ids": list(range(1, 10))},
        {"title": "Celeste", "purchase_price": -1},
        {"title": "Celeste", "purchase_price": INT_MAX + 1},
        {"title": "Celeste", "playtime_minutes": -1},
        {"title": "Celeste", "rating": 0},
        {"title": "Celeste", "rating": 6},
        {"title": "Celeste", "review": "x" * 201},
        {"steam_appid": 0},
        {"steam_appid": INT_MAX + 1},
    ],
)
async def test_invalid_create_is_422(client, auth_headers, bad):
    res = await client.post("/api/entries", json=bad, headers=await auth_headers(A))
    assert res.status_code == 422, res.text


async def test_duplicated_genre_ids_are_one(client, auth_headers):
    created = await entry_of(client, await auth_headers(A), genre_ids=[1, 1])
    assert [g["id"] for g in created["game"]["genres"]] == [1]


async def test_create_uses_defaults(client, auth_headers):
    created = await entry_of(client, await auth_headers(A))
    assert created["status"] == "BACKLOG"
    assert created["playtime_minutes"] == 0
    assert created["source"] == "MANUAL"
    assert created["cost_per_hour"] is None


async def test_time_and_date_formats(client, auth_headers):
    """화면이 믿는 형식이다 ─ 시각은 UTC Z, 날짜는 시각 없이 (CLAUDE.md 함정, ARCHITECTURE 3.1절)"""
    created = await entry_of(client, await auth_headers(A), purchased_at="2026-01-02")
    assert created["created_at"].endswith("Z"), created["created_at"]
    assert created["updated_at"].endswith("Z"), created["updated_at"]
    assert created["purchased_at"] == "2026-01-02"


# ─── 수정 ───────────────────────────────────────────────


@pytest.mark.parametrize(
    "bad",
    [
        {"title": "다른 제목"},
        {"game_id": 1},
        {"source": "STEAM"},
        {"status": "UNKNOWN"},
        {"status": None},
        {"playtime_minutes": None},
        {"genre_ids": [999]},
        {"genre_ids": list(range(1, 10))},
        {"purchase_price": -1},
        {"purchase_price": INT_MAX + 1},
        {"rating": 0},
        {"rating": 6},
        {"review": "x" * 201},
    ],
)
async def test_invalid_update_is_422_and_changes_nothing(client, auth_headers, bad):
    headers = await auth_headers(A)
    before = await entry_of(client, headers, purchase_price=1000, genre_ids=[1])
    res = await client.patch(f"/api/entries/{before['id']}", json=bad, headers=headers)
    assert res.status_code == 422, res.text
    assert (await client.get(f"/api/entries/{before['id']}", headers=headers)).json() == before


async def test_empty_update_changes_nothing(client, auth_headers):
    headers = await auth_headers(A)
    before = await entry_of(client, headers, purchase_price=1000)
    res = await client.patch(f"/api/entries/{before['id']}", json={}, headers=headers)
    assert res.status_code == 200
    assert res.json()["purchase_price"] == 1000


async def test_null_clears_only_optional_fields(client, auth_headers):
    """null은 '지운다'이고 안 보낸 칸은 그대로다"""
    headers = await auth_headers(A)
    before = await entry_of(client, headers, purchase_price=1000, purchased_at="2026-01-02", rating=4, review="좋음", status="CLEARED")
    res = await client.patch(f"/api/entries/{before['id']}", json={"purchase_price": None, "rating": None}, headers=headers)
    after = res.json()
    assert after["purchase_price"] is None
    assert after["rating"] is None
    assert after["purchased_at"] == "2026-01-02"
    assert after["review"] == "좋음"


@pytest.mark.parametrize("entry_id", [0, -1, INT_MAX + 1, 10**30])
@pytest.mark.parametrize("method", ["get", "patch", "delete"])
async def test_out_of_range_id_is_the_same_404(client, auth_headers, method, entry_id):
    headers = await auth_headers(A)
    kwargs = {"json": {}} if method == "patch" else {}
    res = await getattr(client, method)(f"/api/entries/{entry_id}", headers=headers, **kwargs)
    assert res.status_code == 404, res.text
    assert res.json() == {"detail": "기록을 찾을 수 없습니다"}


async def test_other_users_entry_cannot_be_changed(client, auth_headers):
    a = await auth_headers(A)
    b = await auth_headers(B)
    mine = await entry_of(client, a, genre_ids=[1])
    assert (await client.patch(f"/api/entries/{mine['id']}", json={"genre_ids": [2]}, headers=b)).status_code == 404
    assert (await client.delete(f"/api/entries/{mine['id']}", headers=b)).status_code == 404
    again = (await client.get(f"/api/entries/{mine['id']}", headers=a)).json()
    assert [g["id"] for g in again["game"]["genres"]] == [1]


# ─── 목록 ───────────────────────────────────────────────


@pytest.mark.parametrize(
    "params",
    [
        {"limit": 0},
        {"limit": 101},
        {"offset": -1},
        {"status": "UNKNOWN"},
        {"sort": "price"},
        {"genre": 0},
        {"genre": INT_MAX + 1},
        {"limit": "abc"},
    ],
)
async def test_invalid_list_params_are_422(client, auth_headers, params):
    res = await client.get("/api/entries", params=params, headers=await auth_headers(A))
    assert res.status_code == 422, res.text


async def test_pages_do_not_change_total(client, auth_headers):
    headers = await auth_headers(A)
    for i in range(3):
        await entry_of(client, headers, title=f"게임 {i}")
    first = (await client.get("/api/entries", params={"limit": 2}, headers=headers)).json()
    second = (await client.get("/api/entries", params={"limit": 2, "offset": 2}, headers=headers)).json()
    past = (await client.get("/api/entries", params={"limit": 2, "offset": 50}, headers=headers)).json()
    assert (first["total"], len(first["items"])) == (3, 2)
    assert (second["total"], len(second["items"])) == (3, 1)
    assert (past["total"], past["items"]) == (3, [])
    assert not {e["id"] for e in first["items"]} & {e["id"] for e in second["items"]}


# ─── 장르 · 로그인 필요 ─────────────────────────────────


async def test_genres_are_listed_in_id_order(client, auth_headers):
    res = await client.get("/api/genres", headers=await auth_headers(A))
    assert [g["id"] for g in res.json()] == list(range(1, 9))


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/api/genres"),
        ("GET", "/api/entries"),
        ("POST", "/api/entries"),
        ("GET", "/api/entries/1"),
        ("PATCH", "/api/entries/1"),
        ("DELETE", "/api/entries/1"),
        ("GET", "/api/stats"),
        ("GET", "/api/steam/apps?q=ab"),
    ],
)
async def test_everything_needs_login(client, method, path):
    res = await client.request(method, path, json={} if method in ("POST", "PATCH") else None)
    assert res.status_code == 401, res.text
