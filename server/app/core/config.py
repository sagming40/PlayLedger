# ============================================================
# 환경설정 로딩
# .env 파일의 값을 읽어와 Python 객체로 바꿔준다.
# ============================================================

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# 실행 위치와 상관없이 server/.env를 읽는다 (이 파일 = server/app/core/config.py)
SERVER_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # ".env에 필수값과 기본값이 있는 값"이라는 요구 목록이다.
    # 값이 없으면 서버가 시작하는 순간 error를 내고 멈춘다.
    # 조용히 넘어가지 않는 것 자체가 이 방식의 핵심이다
    database_url: str
    # 필수 ─ 없거나 32자보다 짧으면 서버 안 뜸
    # HS256의 키는 SHA-256 출력(32바이트) 이상이어야 한다 (RFC 7518 3.2절). 짧으면 토큰 하나로 키를 대입해 아무나로 위조할 수 있다
    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"            # 기본값이 있으니 .env에 없어도 됨

    # 테스트 전용 DB 주소. 평소 서버 실행엔 필요가 없으므로 default는 빈 문자열이다
    # DATABASE_URL과 달리 "없으면 즉시 멈춤"으로 설정해두지 않는 이유
    # ─ 필수로 설정할 경우 테스트를 돌리고 싶지 않은 사람들도 값을 채워야 서버가 뜬다. (강제성, 종속성 고려)
    test_database_url: str = ""
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 14

    # Steam Web API 키. 게임 목록 미러링 스크립트만 쓰므로 default는 빈 문자열이다
    # 필수로 두면 키가 없는 CI · 다른 기기에서 서버와 테스트까지 뜨지 않는다 (스크립트가 비어 있으면 멈춘다)
    steam_api_key: str = ""

    # Swagger 문서(/docs). 개발에서 쓰므로 기본은 켠다. 운영 .env에서 false로 끈다
    enable_docs: bool = True

    # 어느 파일을 읽을지 알려주는 설정표
    model_config = SettingsConfigDict(
        env_file=SERVER_DIR / ".env",
        env_file_encoding="utf-8",
        # 모르는 키는 무시한다 ─ 운영에서 .env를 하나로 합치면 POSTGRES_PASSWORD 때문에 서버가 안 뜬다
        extra="ignore",
    )


# app 전체가 함께 사용할 설정 꾸러미 하나
# 다른 파일에서는 from app.core.config import settings로 가져다 사용한다.
settings = Settings()
