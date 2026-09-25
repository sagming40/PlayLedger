"""사용자 격리 — A 계정의 기록이 B 계정에 보이지 않는지 확인한다.

M1 완료 기준 첫 줄에 해당하는 테스트 묶음.
"""

A_EMAIL = "alice@example.com"
B_EMAIL = "bob@example.com"


async def create_entry(client, headers, title):
    """보유 기록 하나를 등록하고 응답 본문을 돌려준다.

    fixture가 아니라 그냥 함수인 이유 — pytest가 주입해 줄 필요 없이
    테스트 안에서 내가 원하는 시점에, 원하는 계정으로 부르면 되기 때문.
    """
    res = await client.post(
        "/api/entries",
        json={"title": title, "status": "BACKLOG"},
        headers=headers,
    )
    assert res.status_code == 201, res.json()
    return res.json()


async def test_entries_require_login(client):
    """격리의 전제 조건. 문이 열려 있으면 안쪽 자물쇠는 의미가 없다."""
    res = await client.get("/api/entries")
    assert res.status_code == 401, res.json()


async def test_list_shows_only_own_entries(client, auth_headers):
    """목록 조회는 자기 기록만 보여준다 (M1 완료 기준 첫 줄)."""
    a = await auth_headers(A_EMAIL)
    b = await auth_headers(B_EMAIL)

    await create_entry(client, a, "Hollow Knight")
    await create_entry(client, b, "Celeste")

    # 개수만 보면 '필터가 걸렸다'를 증명하지 못한다. 어떤 게 보이는지까지 확인
    res = await client.get("/api/entries", headers=a)
    assert res.status_code == 200, res.json()
    body = res.json()
    assert body["total"] == 1, body
    assert [item["game"]["title"] for item in body["items"]] == ["Hollow Knight"], body

    res = await client.get("/api/entries", headers=b)
    body = res.json()
    assert body["total"] == 1, body
    assert [item["game"]["title"] for item in body["items"]] == ["Celeste"], body


async def test_other_users_entry_is_not_readable(client, auth_headers):
    """남의 기록을 id로 직접 찔러도 404 (403이 아니다 — 존재 여부조차 안 알려준다)."""
    a = await auth_headers(A_EMAIL)
    b = await auth_headers(B_EMAIL)
    entry = await create_entry(client, a, "Hollow Knight")

    res = await client.get(f"/api/entries/{entry['id']}", headers=b)
    assert res.status_code == 404, res.json()


async def test_other_users_entry_looks_exactly_like_a_missing_one(client, auth_headers):
    """404를 주는 것만으로는 부족하다.

    '남의 것'과 '없는 것'의 응답이 완전히 같아야 존재 여부가 새어 나가지 않는다.
    로그인 실패 메시지를 하나로 통일한 것(UI_DESIGN 3.1절)과 같은 원리 —
    응답이 갈리는 것 자체가 공격자에게는 정보다.
    """
    a = await auth_headers(A_EMAIL)
    b = await auth_headers(B_EMAIL)
    entry = await create_entry(client, a, "Hollow Knight")

    others = await client.get(f"/api/entries/{entry['id']}", headers=b)  # 남의 것
    missing = await client.get("/api/entries/999999", headers=b)         # 없는 것

    assert others.status_code == 404, others.json()
    assert missing.status_code == 404, missing.json()
    # 손 검증 때 content-length 46으로 대조한 것을 코드로 옮긴 것
    assert others.json() == missing.json(), (others.json(), missing.json())


async def test_other_users_entry_is_not_editable(client, auth_headers):
    """404를 주고도 뒤에서 값을 바꿔버렸다면 격리가 아니다. 주인 쪽에서 원본을 확인한다."""
    a = await auth_headers(A_EMAIL)
    b = await auth_headers(B_EMAIL)
    entry = await create_entry(client, a, "Hollow Knight")

    res = await client.patch(
        f"/api/entries/{entry['id']}",
        json={"status": "CLEARED"},
        headers=b,
    )
    assert res.status_code == 404, res.json()

    res = await client.get(f"/api/entries/{entry['id']}", headers=a)
    assert res.status_code == 200, res.json()
    assert res.json()["status"] == "BACKLOG", res.json()


async def test_other_users_entry_is_not_deletable(client, auth_headers):
    """위와 같은 이유 — 응답이 404여도 실제로 지워졌는지는 따로 확인해야 한다."""
    a = await auth_headers(A_EMAIL)
    b = await auth_headers(B_EMAIL)
    entry = await create_entry(client, a, "Hollow Knight")

    res = await client.delete(f"/api/entries/{entry['id']}", headers=b)
    assert res.status_code == 404, res.json()

    res = await client.get(f"/api/entries/{entry['id']}", headers=a)
    assert res.status_code == 200, res.json()


async def test_same_game_can_be_registered_by_both_users(client, auth_headers):
    """중복 방지는 '한 사용자 안에서'다. 다른 사용자까지 막으면 그건 버그다.

    UNIQUE가 (user_id, game_id)가 아니라 game_id 하나로 걸려 있다면 여기서 409가 난다.
    games는 모두가 공유하는 마스터 데이터이고 entries는 개인 것 — 그 경계를 지키는 테스트.
    """
    a = await auth_headers(A_EMAIL)
    b = await auth_headers(B_EMAIL)

    a_entry = await create_entry(client, a, "Hollow Knight")
    b_entry = await create_entry(client, b, "  hollow knight  ")  # 정규화되면 같은 게임

    # 게임 행은 공유, 보유 기록은 별개
    assert a_entry["game"]["id"] == b_entry["game"]["id"], (a_entry, b_entry)
    assert a_entry["id"] != b_entry["id"], (a_entry, b_entry)
    # 공유 게임의 제목은 먼저 등록한 A가 적은 그대로다 ─ B의 입력이 남의 데이터를 바꾸지 않는다
    assert b_entry["game"]["title"] == "Hollow Knight", b_entry

    res = await client.get("/api/entries", headers=a)
    assert res.json()["total"] == 1, res.json()
