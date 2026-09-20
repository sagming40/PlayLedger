# app/core/security.py
"""비밀번호 Hashing, token 발급·검증 담당.
비밀번호 원문과 서명 키는 이 파일 밖으로 나가지 않는다.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import settings

# 해싱 설정(메모리·반복 횟수 등)을 들고 있는 도구 상자
# module 최상단에 딱 하나만 만들어 계속 재사용한다
# 주문 마다 주방을 새로 짓는 건 아니기 때문이다
password_hasher = PasswordHasher()


def hash_password(plain_password: str) -> str:
    """비밀번호 원문을 저장용 해시 String으로 만든다

    고기를 갈아 패티를 만드는 것과 같다 ─ 되돌릴 수 없다
    같은 비밀번호를 두 번 넣어도 매번 다른 결과가 나오는데,
    안에서 각각 다른 새로운 소금(salt)을 무작위로 뿌리기 때문이다
    """
    return password_hasher.hash(plain_password)


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """입력한 비밀번호가 저장된 hash와 일치하는지 확인한다.

    argon2는 일치하지 않으면 예외를 던지기 때문에, 받아서 True/False로 변환해준다.
    argon2를 사용한다는 것을 서버 나머지 코드는 몰라도 되게 만드는 칸막이 역할.
    나중에 라이브러리를 교체해도 이 파일만 수정하면 된다.
    """
    try:
        # 인자 순서 주의 ─ hash가 먼저, 비밀번호가 나중이다.
        password_hasher.verify(stored_hash, plain_password)
    except (VerificationError, InvalidHashError, UnicodeEncodeError):
        # 비밀번호 불일치 / Hash String 손상. 두 가지 상황 모두 "로그인 실패"로 통일한다.
        # 어느 쪽인지 노출시키게 되면 공격에 쉽게 노출된다. (공격자에게 Hint를 주는 셈)
        return False
    return True


def create_access_token(user_id: int) -> str:
    """로그인한 사용자에게 지급할 출입증을 만든다.
    
    비유: 놀이공원 손목 밴드 ─ 놀이공원 입구에서 처음 한 번 확인을 받고 밴드를 받으면,
    그 다음 부터는 놀이기구를 탈 때 다시 보여주지 않아도 된다.
    밴드에는 '누구인지', '유효기간'이 적혀있고, 위조를 막기 위해 놀이공원 전용 인증 도장을 찍는다.
    """
    now = datetime.now(timezone.utc)
    
    # payload = 밴드에 적어 넣을 내용
    # 누구나 접근 가능하므로 비밀 정보는 절대 담지 않는다.
    payload = {
        "sub": str(user_id),   # subject ─ 토큰의 주인. JWT 표준상 String 이어야 한다.
        "iat": now,            # issued at ─ 발급 시각
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> int | None:
    """받은 출입증이 진짜인지 확인하고, 주인의 id를 꺼낸다.
    
    도장이 위조됐거나 유효기간이 지난 경우 None을 반환한다.
    verify_password와 같은 원리 ─ 예외를 내부에서 삼킨 후,
    성공 시 value(값), 실패 시 None 반환으로 약속을 단순하게 만든다.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],   # list ─ 단수 인자와 이름이 다름에 주의
        )
    except jwt.InvalidTokenError:
        # 만료(ExpiredSignatureError)·서명 불일치 등이 전부 이 class 아래에 있다.
        return None
    
    user_id = payload.get("sub")
    return int(user_id) if user_id is not None else None


def create_refresh_token() -> str:
    """재발급용 token을 생성한다. 내용은 없고, 추측 불가능하기만 하면 된다.
    
    비유: 사물함 번호표 ─ 번호표 자체엔 아무런 정보가 없다.
    사물함(DB)까지 가서 직접 대조해야만 누구의 것인지 알 수 있다.
    access 토큰(JWT)이 '읽을 수 있는 출입증'인 것과 정반대이다.
    
    random이 아닌 secrets를 사용하는 이유
    ─ random은 seed를 알면 다음 값이 재현된다. 게임 주사위와 복권 추첨기의 차이와 유사하다.
    """
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    """DB에 저장할 형태로 변환 (ERD 2.2절)
    
    비밀번호와 달리 argon2가 아닌 SHA-256을 사용한다.
    argon2가 느린 이유는 사람이 만든 보안이 약한 비밀번호를 하나씩 대입해보는 공격을 막기 위함이다.
    이 token은 32바이트 무작위값이라 대입이라는 개념 자체가 성립하지 않는다. 느리게 만들 이유가 없다.
    
    같은 입력이면 항상 같은 결과가 나온다. (salt X)
    들어온 token을 해싱하여 DB 값과 바로 대조할 수 있다.
    """
    return hashlib.sha256(token.encode()).hexdigest()
