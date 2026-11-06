# ============================================================
# PlayLedger API 서버 시작점
# ============================================================

import logging
import shutil
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.deps import get_db
from app.routers import auth, genres, entries, stats, steam, steam_link

logger = logging.getLogger("playledger")

# 남은 디스크가 이 비율 아래면 헬스체크가 "disk":"low"를 답한다 (SERVER 1절 감시)
# 23GB 서버에서 약 2.3GB ─ 백업 · 로그 · 이미지가 거의 안 늘어서, 여기까지 오면 무언가 새고 있는 것이다
DISK_LOW_FREE_RATIO = 0.10


def disk_state(path: str = "/") -> str:
    """서버 디스크 여유를 ok / low / error 셋 중 하나로만 답한다 ─ 숫자는 밖에 보이지 않게

    컨테이너 안의 /는 서버 디스크 위에 있다(Docker 저장소와 DB 볼륨이 같은 디스크). 그래서 여기서 재면 서버를 잰 것이다
    """
    try:
        usage = shutil.disk_usage(path)
    except OSError:
        logger.exception("헬스체크: 디스크를 읽지 못함")
        return "error"
    return "low" if usage.free < usage.total * DISK_LOW_FREE_RATIO else "ok"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """서버가 켜 있는 동안 쓰는 것을 준비하고 끝날 때 치운다

    외부 API(Steam)용 클라이언트는 하나를 돌려 쓴다 ─ 만들 때마다 인증서를 읽어 요청을 막는다(약 24ms)
    timeout을 짧게 둔다 ─ Steam이 느려도 등록을 오래 붙잡지 않고 커버 없이 진행한다 (decisions/0008)
    """
    async with httpx.AsyncClient(timeout=5) as client:
        app.state.http = client
        yield


# 가게 안의 주방 부분. 이 app 객체가 앞으로 모든 요청의 출발점이 된다.
# title은 Swagger 문서 맨 위에 표시되는 이름이다.
# 운영에서는 ENABLE_DOCS=false로 문서 주소를 없앤다 ─ API 전체 지도를 공개할 이유가 없다
app = FastAPI(
    title="PLAYLEDGER API",
    lifespan=lifespan,
    docs_url="/docs" if settings.enable_docs else None,
    redoc_url="/redoc" if settings.enable_docs else None,
    openapi_url="/openapi.json" if settings.enable_docs else None,
)
app.include_router(auth.router)
app.include_router(entries.router)
app.include_router(genres.router)
app.include_router(steam.router)
app.include_router(steam_link.router)
app.include_router(stats.router)


def _safe_text(value: object) -> str | int:
    """UTF-8로 바꿀 수 없는 글자를 치운다 ─ 응답을 만들다가 500이 되면 안 된다"""
    if isinstance(value, int):
        return value
    return str(value).encode("utf-8", "replace").decode("utf-8")


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """422 ─ 어느 칸이 왜 틀렸는지만 돌려준다 (ARCHITECTURE 3.9절)

    기본 응답은 보낸 값(input)까지 되돌려 준다. 짧은 비밀번호가 응답 본문에 찍히고,
    깨진 글자(서로게이트)가 들어 있으면 응답을 UTF-8로 만들다가 500이 된다
    """
    issues = [
        {
            "type": issue["type"],
            "loc": [_safe_text(part) for part in issue["loc"]],
            "msg": _safe_text(issue["msg"]),
        }
        for issue in exc.errors()
    ]
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content={"detail": issues})


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """예상 못 한 오류 ─ 원인은 로그에만 남기고, 화면에는 내부 사정을 알리지 않는다"""
    logger.exception("처리하지 못한 오류: %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "서버에 문제가 생겼습니다. 잠시 후 다시 시도해 주세요"},
    )


# @app.get(...)은 이 주소로 GET 요청이 오면 바로 아래 함수를 실행하라는 표지판
# 주소가 /health가 아닌 /api/health인 이유
# ─ 추후 Vue 개발 서버가 /api로 시작하는 요청만 Backend로 넘기도록 분기하기 위해서다
@app.get("/api/health")
async def health_check(response: Response, db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """운영 환경이 "살아 있나"를 물어보는 곳 ─ DB에 닿지 못하면 503

    서버만 살아 있고 DB가 죽어 있으면 모든 요청이 실패한다. 그 상태를 ok라고 답하면 안 된다

    disk는 status를 바꾸지 않는다 ─ 503이 되면 Docker가 api를 unhealthy로 보고, play-release가
    "새 버전이 안 살아났다"며 되돌리기를 시작한다. 디스크는 새 버전 탓이 아니다. 밖의 uptime 감시만 따로 본다
    """
    disk = disk_state()
    try:
        await db.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError):
        logger.exception("헬스체크: DB에 닿지 못함")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "error", "database": "error", "disk": disk}
    return {"status": "ok", "database": "ok", "disk": disk}
