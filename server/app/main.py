# ============================================================
# PlayLedger API 서버 시작점
# ============================================================

from fastapi import FastAPI

from app.routers import auth

# 가게 안의 주방 부분. 이 app 객체가 앞으로 모든 요청의 출발점이 된다.
# title은 Swagger 문서 맨 위에 표시되는 이름이다.
app = FastAPI(title="PLAYLEDGER API")
app.include_router(auth.router)


# @app.get(...)은 이 주소로 GET 요청이 오면 바로 아래 함수를 실행하라는 표지판
# 주소가 /health가 아닌 /api/health인 이유
# ─ 추후 Vue 개발 서버가 /api로 시작하는 요청만 Backend로 넘기도록 분기하기 위해서다
@app.get("/api/health")
async def health_check():
    # server가 살아있는지 확인하는 요청에 살아있다라고 대답만 하는 함수
    # docker-compose의 healthcheck가 pg_isready로 DB에 knock한 것과 같은 역할이다.
    return {"status": "ok"}
