# app/scripts/sync_steam_apps.py
"""Steam 게임 목록을 steam_apps로 미러링한다 (decisions/0008)

실행: server/에서 python -m app.scripts.sync_steam_apps
스케줄러가 생기는 M7 전까지는 손으로 돌린다. 여러 번 돌려도 행이 늘지 않는다.
"""

import asyncio
import sys
import time

import httpx
from sqlalchemy import func, select

from app.core.config import settings
from app.core.db import AsyncSessionLocal, engine
from app.models.steam_app import SteamApp
from app.services.steam import SteamSyncError, sync_steam_apps


async def main() -> int:
    started = time.perf_counter()
    try:
        async with AsyncSessionLocal() as db, httpx.AsyncClient(timeout=60) as client:
            received = await sync_steam_apps(db, client, settings.steam_api_key)
            rows = await db.scalar(select(func.count()).select_from(SteamApp))
    except SteamSyncError as e:
        print(f"실패: {e}", file=sys.stderr)   # 메시지에 키가 없음을 서비스가 보장한다
        return 1
    finally:
        await engine.dispose()

    print(f"받은 게임 {received}건 · steam_apps {rows}행 · {time.perf_counter() - started:.1f}초")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
