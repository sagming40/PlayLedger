# app/schemas/stats.py
# S-05 통계 응답 모양 (DESIGN 3.5절, REQUIREMENTS 5장)

from pydantic import BaseModel


class IdleGame(BaseModel):
    """오래 방치된 게임 한 줄"""

    entry_id: int   # 누르면 S-04 상세로 간다
    title: str
    cover_url: str | None
    idle_days: int


class CostlyGame(BaseModel):
    """시간당 비용이 높은 게임 한 줄"""

    entry_id: int
    title: str
    cover_url: str | None
    cost_per_hour: int


class GenreStat(BaseModel):
    """장르 하나의 숫자 (REQUIREMENTS F-11)"""

    genre_id: int
    name: str
    total: int     # 이 장르의 보유 게임 수
    started: int   # 그중 미시작을 뺀 수 ─ 완주율의 분모
    cleared: int
    completion_rate: float | None         # %. 시작한 게임이 없으면 None
    avg_playtime_minutes: int | None      # 시작한 게임의 평균. 시작한 게임이 없으면 None


class StatsRead(BaseModel):
    total: int
    backlog: int
    abandoned_rate: float | None    # 사장률(%). 게임이 0개면 None
    completion_rate: float | None   # 완주율(%). 시작한 게임이 없으면 None
    longest_idle: list[IdleGame]
    highest_cost: list[CostlyGame]
    genres: list[GenreStat]
