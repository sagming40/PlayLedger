"""보유 기록 수정 · 삭제 동시 실행 ─ 두 기기에서 한쪽은 수정을 저장하고 한쪽은 삭제하는 상황.

수정이 행을 읽은 뒤 삭제가 끝나면 UPDATE가 0행이 되어 StaleDataError(500)가 난다.
그 틈을 Entry 행 잠금(FOR UPDATE)으로 막는다. 이 TEST가 그 잠금을 지킨다.
"""

import asyncio

import pytest
from sqlalchemy import text

from app.routers import entries

EMAIL = "alice@example.com"

# 잠금을 기다리는 삭제가 있는지 DB에게 직접 묻는다
# 삭제도 기록을 FOR UPDATE로 먼저 읽는다 ─ 이 쿼리를 기다리는 쪽은 수정이 잡은 잠금 뒤에 선 삭제뿐이다
WAITING_DELETES = text(
    "SELECT count(*) FROM pg_stat_activity "
    "WHERE wait_event_type = 'Lock' AND query ILIKE '%FROM entries%FOR UPDATE%'"
)


async def test_delete_waits_while_patch_holds_the_row(client, auth_headers, session_factory, monkeypatch):
    """수정이 행을 읽은 직후 삭제가 들어오면, 삭제는 수정이 끝날 때까지 기다린다.

    요청 순서를 우연에 맡기지 않으려고 읽은 직후에 삭제를 끼워 넣는다.
    "잠시 뒤 안 끝났다"로 판정하지 않는다 ─ 새 DB 연결이 약 2초 걸려서 잠금이 없어도 안 끝나 있다.
    FOR UPDATE를 지우면 삭제가 대기 없이 끝나 pytest.fail에 걸린다.
    """
    headers = await auth_headers(EMAIL)
    res = await client.post(
        "/api/entries",
        json={"title": "Hollow Knight", "status": "BACKLOG"},
        headers=headers,
    )
    assert res.status_code == 201, res.json()
    entry_id = res.json()["id"]

    real_get_entry = entries.get_entry
    remove = None

    async def get_entry_then_delete(db, **kwargs):
        nonlocal remove
        found = await real_get_entry(db, **kwargs)
        if remove is None:  # 수정 요청의 첫 읽기에서 한 번만
            remove = asyncio.create_task(client.delete(f"/api/entries/{entry_id}", headers=headers))
            async with session_factory() as watcher:
                for _ in range(150):
                    if remove.done():
                        pytest.fail("삭제가 기다리지 않고 끝났다 ─ 행이 잠기지 않았다")
                    if await watcher.scalar(WAITING_DELETES):
                        break
                    # pg_stat_activity는 트랜잭션 안에서 값이 고정된다 ─ 끝내야 새 값을 본다
                    await watcher.rollback()
                    await asyncio.sleep(0.1)
                else:
                    pytest.fail("삭제가 15초 안에 잠금 대기에 들어가지 않았다")
        return found

    monkeypatch.setattr(entries, "get_entry", get_entry_then_delete)

    patched = await client.patch(f"/api/entries/{entry_id}", json={"purchase_price": 1}, headers=headers)
    removed = await remove

    # 수정의 commit 직후 삭제가 먼저 끝나면 다시 읽을 때 기록이 없다 ─ 그때는 없는 기록과 같은 404
    assert patched.status_code in (200, 404), patched.text
    assert removed.status_code == 204, removed.text
    assert (await client.get(f"/api/entries/{entry_id}", headers=headers)).status_code == 404
