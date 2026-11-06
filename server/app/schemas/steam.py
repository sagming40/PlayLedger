# app/schemas/steam.py
# Steam 검색 응답 모양

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
