# ============================================================
# 환경설정 로딩
# .env 파일의 값을 읽어와 Python 객체로 바꿔준다.
# ============================================================

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ".env에 반드시 있어야 하는 값이다"라는 요구 목록이다.
    # 값이 없으면 서버가 시작하는 순간 error를 내고 멈춘다.
    # 조용히 넘어가지 않는 것 자체가 이 방식의 핵심이다
    database_url: str

    # 어느 파일을 읽을지 알려주는 설정표
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


# app 전체가 함께 사용할 설정 꾸러미 하나
# 다른 파일에서는 from app.core.config import settings로 가져다 사용한다.
settings = Settings()
