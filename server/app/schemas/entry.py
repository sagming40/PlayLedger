# app/schemas/entry.py
# 보유 기록의 입력(등록) · 출력(응답) 모양 (ERD 2.6절)

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.normalize import normalize_title
from app.schemas.game import GameRead

# 허용되는 상태값 ─ DB의 CHECK와 같은 목록. Literal = "이 중 하나만"
# 비유: 자판기 버튼. 없는 버튼은 누를 수 없다 (다른 값이 오면 422)
EntryStatus = Literal["BACKLOG", "PLAYING", "CLEARED", "ON_HOLD", "DROPPED"]

# PostgreSQL integer의 최댓값 (약 21억)
# Python int는 크기 제한이 없어서, 21억 보다 큰 수가 들어오면 DB에 들어가는 순간 터진다 → 500
# 들어오기 전에 막아야 422로 끝난다
INT_MAX = 2_147_483_647


class EntryCreate(BaseModel):
    """보유 기록 등록 요청

    비유: 입국 심사대. 서류 양식이 틀리면 돌려보낸다(422)
    """

    # 정의되지 않은 field는 거부한다 (default = '조용히 무시')
    # source · steam_appid를 보내도 통과하지 않는다 ─ 두 값은 서버가 정한다
    # 조용히 무시하면 "보냈는데 반영이 되지 않는 이유"를 알 수 없다
    model_config = ConfigDict(extra="forbid")

    title: str = Field(max_length=200)

    # 등록 form의 default가 '시작 안 됨'이므로 생략하면 BACKLOG
    status: EntryStatus = "BACKLOG"

    # 장르 id 목록. 고정 장르가 8개이므로 그보다 많은 경우는 존재할 수 없다
    # Annotated = '목록 안의 각 숫자'에도 범위를 지정 한다 (id는 1 이상, integer 범위 안)
    genre_ids: list[Annotated[int, Field(ge=1, le=INT_MAX)]] = Field(
        default_factory=list, max_length=8
    )

    purchased_at: date | None = None
    purchase_price: int | None = Field(default=None, ge=0, le=INT_MAX)
    playtime_minutes: int = Field(default=0, ge=0, le=INT_MAX)
    rating: int | None = Field(default=None, ge=1, le=5)
    review: str | None = Field(default=None, max_length=200)

    @field_validator("title")
    @classmethod
    def check_title(cls, v: str) -> str:
        """정규화했을 때 빈 값이거나 길이가 너무 길면 거부한다 (ERD 2.4절 4단계)

        결과는 버리고 검사만 한다 ─ title_norm은 서비스가 다시 계산한다
        입구(schema)만 신뢰하지 않는 것이 find_or_create_game의 원칙이다
        """
        normalize_title(v)   # 문제가 있으면 예외 → 422
        return v.strip()


class EntryRead(BaseModel):
    """보유 기록 응답"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    game: GameRead
    status: EntryStatus
    purchased_at: date | None
    purchase_price: int | None
    playtime_minutes: int
    rating: int | None
    review: str | None
    source: str
    created_at: datetime
    updated_at: datetime


class EntryListResponse(BaseModel):
    """목록 응답 ─ 이번 페이지의 기록들 + 전체 개수

    비유: 택배 상자에 물건과 함께 "총 42개 중 20개" 쪽지를 넣어 보내는 것
    개수가 적혀있어야 화면이 "총 42개 · 미시작 18개" 요약 줄을 그릴 수 있다 (UI_DESIGN 3.2절)
    """

    items: list[EntryRead]
    total: int


class EntryUpdate(BaseModel):
    """보유 기록 수정 요청 (PATCH)

    모든 항목이 선택이고, 기본값은 전부 None이다
    "보내지 않음"과 "null로 보냄"은 model_dump(exclude_unset=True)로 구분한다 ─ router 참고
    비유: 주문서 수정 요청서. 빈칸 → "건드리지 말 것", 취소선 → "삭제"
    """

    # title은 아예 받지 않는다 ─ extra="forbid"에 걸림 (422, ERD 2.6절)
    # 제목을 수정하는 것은 이 기록이 가리키는 게임 자체를 갈아 끼워버리는 것이라 허용하지 않는다
    model_config = ConfigDict(extra="forbid")

    status: EntryStatus | None = None
    genre_ids: list[Annotated[int, Field(ge=1, le=INT_MAX)]] | None = Field(
        default=None, max_length=8
    )
    purchased_at: date | None = None
    purchase_price: int | None = Field(default=None, ge=0, le=INT_MAX)
    playtime_minutes: int | None = Field(default=None, ge=0, le=INT_MAX)
    rating: int | None = Field(default=None, ge=1, le=5)
    review: str | None = Field(default=None, max_length=200)
