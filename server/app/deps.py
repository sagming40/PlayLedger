# app/deps.py
"""요청마다 필요한 준비물. 계층이 아니라, 계층을 가로지른다. (ARCHITECTURE 2.2절)"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """요청 하나가 사용할 DB 세션을 빌려주고, 사용이 끝나면 반납한다.

    return이 아닌 yield을 사용한 것이 핵심이다.
    yield ─ "여기까지 만들어서 건네주고, 사용하는 쪽이 끝나면 이 줄 다음부터 이어서 실행"
    비유: 도서관 사서가 책을 대여해주고 반납되면 다시 서가 제자리에 꽂아두는 것과 같다.
    async with가 반납(close)을 자동으로 맡는다.
    """
    async with AsyncSessionLocal() as session:
        yield session
