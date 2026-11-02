# app/schemas/steam.py
# Steam 검색 응답 모양

from pydantic import BaseModel, ConfigDict


class SteamAppRead(BaseModel):
    """검색 후보 하나. 이름은 미러의 영어 이름이다 (decisions/0008)"""

    model_config = ConfigDict(from_attributes=True)

    appid: int
    name: str
