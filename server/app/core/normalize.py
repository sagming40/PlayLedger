# app/core/normalize.py
"""입력값을 '비교할 수 있는 모양'으로 바꾸는 규칙 모음. (ERD 2.1 · 2.4절, ARCHITECTURE 2.2절)

오직 "규칙"만 정해둔다. DB · 요청은 신경쓰지 않는다.
비유: 도량형 기준표. 저울(schema)도 창고(service)도 표(core/normalize.py)를 보고 잰다.
기준표가 창고마다 각각 존재하게 되면 동일한 물건의 무게가 창고마다 들쭉날쭉 해진다.
"""

import unicodedata

# games.title_norm 컬럼 길이와 같아야 한다 (ERD 2.4절 ─ varchar(200))
TITLE_NORM_MAX_LENGTH = 200


def normalize_title(title: str) -> str:
    """게임 제목을 중복 판별용 형태로 변환한다

    4단계를 순차적으로 거친다. 하나라도 건너뛰면 결과가 달라진다.
    비유: 세탁 → 헹굼 → 탈수 → 세탁물 확인.
    순서가 바뀐다면 빨래라는 행동 자체가 성립되지 않는다.
    """

    # 1단계 · NFKC ─ 형태만 다른 같은 글자를 하나로 맞춘다
    # 전각 'Ｆ' → 'F', 로마 숫자 한 글자 'Ⅶ' → 'VII'
    # 비유: 손글씨든 인쇄된 글자체든 동일하게 읽어주는 것
    text = unicodedata.normalize("NFKC", title)

    # 2단계 · casefold ─ lower()보다 강한 소문자화
    # lower()는 'ß'를 그대로 두지만 casefold()는 'ss'로 변환한다
    # 비유: 대소문자 뿐만 아니라 '같은 소리의 다른 철자'까지 맞추는 것
    text = text.casefold()

    # 3단계 · 글자와 숫자만 남긴다 (공백 · 기호 · 따옴표 전부 제거)
    # isalnum()은 한글 · 일본어 · 악센트 문자도 '글자'로 인정한다
    # 비유: 체에 걸러서 알맹이만 남기기
    text = "".join(ch for ch in text if ch.isalnum())

    # 4단계 · 검품 ─ 원본이 아니라 '걸러낸 결과'를 검사한다
    # "!!!" 경우, 원본에는 글자가 존재하지만 걸러지고 난 후에는 빈 값이다
    if not text:
        raise ValueError("제목에는 반드시 글자 혹은 숫자가 하나 이상 필요합니다")

    # NFKC는 글자 수를 늘릴 수 있다 ─ 한 글자가 18글자로 펼쳐지는 문자도 있다
    # 원본이 200자 안이어도 결과가 넘칠 수 있으므로 한 번 더 막는다
    if len(text) > TITLE_NORM_MAX_LENGTH:
        raise ValueError(f"제목이 너무 깁니다 (최대 {TITLE_NORM_MAX_LENGTH}자)")

    return text


def normalize_email(email: str) -> str:
    """이메일을 비교할 수 있는 형태로 변환한다. (ERD 2.1절)

    제목과 달리 앞뒤 공백 제거 + 소문자까지만 변환한다
    이메일은 '메일이 실제로 보내져야 하는 주소'이기 때문에 기호를 지우거나
    casefold로 철자를 바꿔버리면 아예 다른 주소가 되어버린다.

    비유: 제목은 도서관 색인(Index) 카드라 마음대로 다듬어도 되지만,
    택배 송장(이메일)은 송장 번호 자체를 바꿔버리면 엉뚱한 주소로 배송이 되어버린다.
    """
    return email.strip().lower()
