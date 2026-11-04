# 운영 API 이미지 (PLAN M5, 구성은 deploy/compose.prod.yaml)
# 테스트 패키지(requirements-dev.txt)는 넣지 않는다 ─ 운영에 필요 없는 코드는 공격 면적일 뿐이다
FROM python:3.13-slim

# 로그가 버퍼에 고이지 않고 바로 나오게, 쓸모없는 .pyc를 만들지 않게 (컨테이너가 읽기 전용이다)
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 코드 · 마이그레이션만 복사한다. .env · venv · tests는 .dockerignore로 빠진다
COPY app app
COPY alembic alembic
COPY alembic.ini .

# 로그인 불가 전용 계정 ─ 앱이 털려도 root 권한은 없다
RUN useradd --system --no-create-home --shell /usr/sbin/nologin app
USER app

EXPOSE 8000

# 비밀값 없이 살아 있는지만 본다. curl을 넣지 않으려고 python으로 부른다
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
  CMD ["python", "-c", "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"]

# 워커는 1개 ─ 요청 제한이 프로세스 메모리에 있어 워커를 늘리면 제한도 그만큼 늘어난다 (core/rate_limit.py)
# --forwarded-allow-ips ─ Caddy의 고정 IP가 보낸 X-Forwarded-For만 믿는다 (compose.prod.yaml)
#   이게 없으면 모든 사용자가 Caddy IP 하나로 묶여 요청 제한이 서로를 막고, 넓게 열면 헤더로 IP를 속일 수 있다
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "172.30.0.10", "--no-server-header"]
