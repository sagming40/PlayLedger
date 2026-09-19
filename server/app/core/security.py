# app/core/security.py
"""비밀번호 해싱 담당. 원문은 이 파일 밖으로 절대 나가지 않는다."""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

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
