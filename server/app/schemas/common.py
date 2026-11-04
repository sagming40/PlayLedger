# app/schemas/common.py
"""여러 요청이 같이 쓰는 입력 타입"""

from datetime import date
from typing import Annotated

from pydantic import AfterValidator


def contains_broken_text(value: str) -> bool:
    """DB에 넣거나 UTF-8로 바꿀 수 없는 글자가 있는가

    NUL(\\x00) ─ PostgreSQL 문자열에 들어가지 못해 500이 된다
    짝 없는 서로게이트(\\ud800 ~ \\udfff) ─ JSON으로는 올 수 있지만 UTF-8로 바꿀 수 없어 500이 된다
    """
    return any(ch == "\x00" or "\ud800" <= ch <= "\udfff" for ch in value)


def _reject_broken_text(value: str) -> str:
    if contains_broken_text(value):
        raise ValueError("사용할 수 없는 문자가 포함되어 있습니다")
    return value


def _reject_absurd_date(value: date) -> date:
    # 게임을 산 날짜로 있을 수 없는 값 ─ 입력 실수이고, 방치일수 · 통계 숫자를 망가뜨린다
    if not date(1970, 1, 1) <= value <= date(2100, 12, 31):
        raise ValueError("날짜를 다시 확인해 주세요")
    return value


# 사람이 적는 문자열은 전부 이 타입으로 받는다
CleanStr = Annotated[str, AfterValidator(_reject_broken_text)]
PurchaseDate = Annotated[date, AfterValidator(_reject_absurd_date)]
