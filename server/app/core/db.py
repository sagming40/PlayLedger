# ============================================================
# DATABASE 연결
# App 전체가 공유하는 Engine(커넥션 풀)을 하나 만든다
# ============================================================

from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings


# ENGINE = DB 연결을 관리하는 사무소
# 접속 때마다 매번 새로 문을 두드리는 대신, 열어두었던 연결을 빌려주고 돌려받는다.
# echo=True로 설정하면 SQLAlchemy가 실제로 만들어 내보내는 SQL이 Terminal에 찍힌다.
engine = create_async_engine(settings.database_url, echo=False)
