"""S-04 상세 화면이 기대는 서버 동작 — 시간당 비용 · 상태만 바꾸기 · 평점 보존.

DESIGN 3.4 · 4.3절, REQUIREMENTS 5.1절.
"""

import pytest

EMAIL = "alice@example.com"


async def create_entry(client, headers, **fields):
    body = {"title": "Hollow Knight", "status": "BACKLOG", **fields}
    res = await client.post("/api/entries", json=body, headers=headers)
    assert res.status_code == 201, res.json()
    return res.json()


@pytest.mark.parametrize(
    ("price", "minutes", "expected"),
    [
        (66000, 2400, 1650),  # REQUIREMENTS 5.1절 예시 A ─ 40시간
        (66000, 120, 33000),  # 예시 B ─ 2시간
        (66000, 3744, 1058),  # 목업 Detail ─ 62.4시간, 1057.69… → 1058
        (100, 120, 50),  # 0.5 경계 ─ 50원 정확히
        (1, 120, 1),  # 0.5원 → 올림 (round()였다면 0)
        (0, 600, 0),  # 무료 게임 ─ 계산할 수 없는 게 아니라 0원/h
        (66000, 0, None),  # 플레이타임 0 → 화면 '—' (DESIGN 3.4절)
        (None, 600, None),  # 구매가를 안 적음
    ],
)
async def test_cost_per_hour(client, auth_headers, price, minutes, expected):
    headers = await auth_headers(EMAIL)
    entry = await create_entry(client, headers, purchase_price=price, playtime_minutes=minutes)
    assert entry["cost_per_hour"] == expected, entry

    # 단건 조회에도 같은 값이 온다 (S-04는 단건 조회로 그린다)
    res = await client.get(f"/api/entries/{entry['id']}", headers=headers)
    assert res.json()["cost_per_hour"] == expected, res.json()


async def test_cost_per_hour_follows_playtime_change(client, auth_headers):
    """플레이타임을 고치면 시간당 비용도 새 값으로 계산된다 ─ 저장된 값이 아니라 그때그때 계산"""
    headers = await auth_headers(EMAIL)
    entry = await create_entry(client, headers, purchase_price=66000, playtime_minutes=0)
    assert entry["cost_per_hour"] is None

    res = await client.patch(f"/api/entries/{entry['id']}", json={"playtime_minutes": 2400}, headers=headers)
    assert res.status_code == 200, res.json()
    assert res.json()["cost_per_hour"] == 1650


async def test_status_only_patch_keeps_everything_else(client, auth_headers):
    """상세 화면은 상태만 보낸다 ─ 나머지 값이 지워지면 안 된다 (DESIGN 3.4절)"""
    headers = await auth_headers(EMAIL)
    entry = await create_entry(
        client,
        headers,
        status="CLEARED",
        purchase_price=66000,
        playtime_minutes=3744,
        purchased_at="2026-01-15",
        rating=4,
        review="엔딩 보고 한참 멍했음",
    )

    res = await client.patch(f"/api/entries/{entry['id']}", json={"status": "PLAYING"}, headers=headers)
    assert res.status_code == 200, res.json()
    body = res.json()
    assert body["status"] == "PLAYING"
    for key in ("purchase_price", "playtime_minutes", "purchased_at", "rating", "review", "cost_per_hour"):
        assert body[key] == entry[key], (key, body)


async def test_rating_survives_replay(client, auth_headers):
    """CLEARED → PLAYING → CLEARED로 돌아와도 이전 평점이 남는다 (DESIGN 4.3절, PLAN M3 완료 기준)"""
    headers = await auth_headers(EMAIL)
    entry = await create_entry(client, headers, status="CLEARED", rating=5, review="최고")

    for next_status in ("PLAYING", "CLEARED"):
        res = await client.patch(f"/api/entries/{entry['id']}", json={"status": next_status}, headers=headers)
        assert res.status_code == 200, res.json()

    body = res.json()
    assert (body["status"], body["rating"], body["review"]) == ("CLEARED", 5, "최고"), body


@pytest.mark.parametrize("entry_id", ["99999999999", "2147483648", "0", "-1"])
async def test_out_of_range_id_is_not_found(client, auth_headers, entry_id):
    """주소창에 integer 범위를 넘는 id를 쳐도 500이 아니라 404 (상세 화면 주소는 /library/:id)

    본문도 '없는 기록'과 같아야 한다 ─ 단건 · 수정 · 삭제 세 곳 모두
    """
    headers = await auth_headers(EMAIL)
    missing = await client.get("/api/entries/12345", headers=headers)

    for method, kwargs in (("GET", {}), ("PATCH", {"json": {"status": "PLAYING"}}), ("DELETE", {})):
        res = await client.request(method, f"/api/entries/{entry_id}", headers=headers, **kwargs)
        assert res.status_code == 404, (method, res.json())
        assert res.json() == missing.json(), method
