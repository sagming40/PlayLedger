# app/schemas/game.py
# 게임 정보를 밖으로 내보낼 때의 모양

from pydantic import BaseModel, ConfigDict

from app.schemas.genre import GenreRead


class GameRead(BaseModel):
    """보유 기록 응답 안에 들어가는 게임 정보

    비유: 택배 상자(보유 기록) 안에 들어 있는 작은 상자(게임)
    게임은 공유 데이터라 사용자별 정보(상태, 평점)는 없고 바깥 상자(보유 기록)에 있다
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str                # title_norm은 내보내지 않는다 ─ 판별용 내부 값
    genres: list[GenreRead]   # game.genres(relationship)를 GenreRead 형태로 변환
