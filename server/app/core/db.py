# ============================================================
# DATABASE 연결
# App 전체가 공유하는 Engine(커넥션 풀)을 하나 만든다
# ============================================================

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession

from app.core.config import settings


# ENGINE = DB 연결을 관리하는 사무소
# 접속 때마다 매번 새로 문을 두드리는 대신, 열어두었던 연결을 빌려주고 돌려받는다.
# echo=True로 설정하면 SQLAlchemy가 실제로 만들어 내보내는 SQL이 Terminal에 찍힌다.
# pool_pre_ping ─ 빌려주기 전에 연결이 살아 있는지 확인한다. DB가 재시작된 뒤 첫 요청이 500이 되지 않게
# hide_parameters ─ 오류 로그에 SQL 값을 찍지 않는다. 가입 오류 로그에 이메일 · 비밀번호 해시가 남으면 안 된다
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    hide_parameters=True,
)


AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False,
)
