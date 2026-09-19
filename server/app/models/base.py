# ================================================================
# 모든 테이블의 공통 부모
# base.py를 상속 받으면 Base.metadata(출석부)에 이름이 자동으로 올라간다. 
# ================================================================

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


# 제약조건 이름을 짓는 규칙표
# 규칙을 정해두지 않으면 PostgreSQL이 자동으로 제약 조건명을 붙여버린다.
# 나중에 어떤 CHECK 제약 하나를 삭제해야 할 상황이 발생했을 때, 
# 정확한 이름을 몰라 삭제를 못 하게 될 경우가 발생할 수도 있다.
# 비유: 택배 상자에 미리 송장 번호 규칙을 정해두는 것과 같다.
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",      # 일반 index
    "uq": "uq_%(table_name)s_%(column_0_name)s",      # UNIQUE
    "ck": "ck_%(table_name)s_%(constraint_name)s",  # CHECK
    "fk": "fk_%(table_name)s_%(column_0_name)s",      # ForeignKey (외래키)
    "pk": "pk_%(table_name)s",                        # PrimaryKey (기본키)
}

class Base(DeclarativeBase):
    # 출석부에 작명 규칙을 달아둔다. 아래 추가될 모든 테이블에 적용된다.
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
