# ============================================================
# 만든 model들을 한데 모은다.
# 모델을 import하면 Base.metadata(출석부)에 등록된다.
# Alembic이 테이블을 알아내는 유일한 통로이다.
# ============================================================

from app.models.base import Base
from app.models.entry import Entry
from app.models.game import Game, Genre, game_genres
from app.models.user import RefreshToken, User

# import만 하고 사용하지 않는 코드라 linter가 "사용하지 않는 import"로 지운다
# __all__에 적어두면 "일부러 내보내는 것"이라고 알려줄 수 있다.
__all__ = ["Base", "Entry", "Game", "Genre", "RefreshToken", "User", "game_genres"]
