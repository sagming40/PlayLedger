# app/schemas/steam.py
# Steam 검색 응답 모양

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SteamAppRead(BaseModel):
    """검색 후보 하나. 이름은 미러의 영어 이름이다 (decisions/0008)"""

    model_config = ConfigDict(from_attributes=True)

    appid: int
    name: str


class SteamLinkStart(BaseModel):
    """연결 시작 응답 ─ 화면은 이 주소로 페이지를 옮긴다 (fetch가 아니라 location 이동)

    시작을 페이지 이동(GET)으로 받지 않는 이유: access 토큰은 메모리에만 있어서 페이지 이동에는 실리지 않는다
    """

    redirect_url: str


class SteamSyncRead(BaseModel):
    """동기화 결과 요약 (ARCHITECTURE 5.1절, services/steam_sync.py SyncResult)"""

    model_config = ConfigDict(from_attributes=True)

    added: int
    updated: int
    unchanged: int
    skipped_manual: int
    skipped_limit: int
    skipped_no_title: int
    same_title_manual: int
    synced_at: datetime
    # 이번에 못 받았으면 옛 이름, 한 번도 못 받았으면 null (services/steam.py fetch_persona_name)
    steam_persona_name: str | None
