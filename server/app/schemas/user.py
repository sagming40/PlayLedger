# app/schemas/user.py
"""회원 관련 요청·응답의 '모양'. 실제 방어선. (ARCHITECTURE 2.1절)"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    """회원가입 요청으로 들어오는 것.

    입국 심사대 같은 역할이다. 통과하지 못한 데이터는
    router 함수 안으로 절대 들어올 수 없다.
    """

    email: EmailStr                                       # 형식이 email인지 검사
    password: str = Field(min_length=8, max_length=128)
    nickname: str = Field(min_length=2, max_length=30)    # ERD ─ varchar(30)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        """Email을 소문자로 통일한다 (ERD 2.1절)

        title_norm과 완전히 같은 원리 ─ 들어오는 경로가 어디든
        서버에서 항상 같은 모양으로 변환하여 저장한다.
        화면에서 소문자로 변환해주는 것에 의존하면 안 된다.
        """
        return value.strip().lower()

    @field_validator("nickname", mode="before")
    @classmethod
    def strip_nickname(cls, value: str) -> str:
        """앞뒤 공백을 먼저 털어낸다

        mode="before"가 핵심 ─ 길이 검사보다 선행된다.
        선행되지 않으면 이미 공백이 통과된 후 공백 상태가 저장 되어버린 상태에서 
        공백 검사가 진행되어 빈 닉네임(예: "  " min_length=2)이 생겨버린다.
        즉, 검사 순서 하나로 구멍이 생기는 셈이다.
        """
        return value.strip() if isinstance(value, str) else value


class UserRead(BaseModel):
    """회원 정보 응답으로 나가는 것

    적지 않은 필드는 절대 밖으로 나가지 못한다
    password_hash가 목록에 존재하지 않는 것이 class의 존재 이유이다
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    nickname: str
    created_at: datetime
