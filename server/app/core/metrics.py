# app/core/metrics.py
"""숫자 지표의 계산식 (REQUIREMENTS 5장)

응답 하나하나와 통계 집계가 같은 식을 쓰게 한 곳에 둔다.
곳곳에 따로 적으면 반올림이 제각각이 되어 상세 화면과 통계 화면의 숫자가 어긋난다.
"""


def cost_per_hour(price: int | None, minutes: int) -> int | None:
    """시간당 비용(원) = 구매가 ÷ 플레이타임(시간) (REQUIREMENTS 5.1절)

    플레이타임이 0이거나 구매가가 없으면 계산할 수 없다 → None (화면은 '—')
    무료 게임(0원)은 0원/h ─ 계산할 수 없는 게 아니라 정말 0이다
    """
    if price is None or minutes == 0:
        return None
    # 정수로만 계산해 원 단위로 반올림(0.5는 올림)한다
    # round()는 0.5를 짝수 쪽으로 보내고(은행가 반올림), 시간으로 먼저 나누면 소수 오차가 끼어든다
    # 구매가 × 60 ÷ 분 = 구매가 ÷ 시간. 분자에 분의 절반을 더하고 나누면 반올림이 된다
    return (price * 60 * 2 + minutes) // (minutes * 2)


def percent(part: int, whole: int) -> float | None:
    """비율(%), 소수 한 자리 (REQUIREMENTS 5.2 · 5.3절)

    분모가 0이면 None ─ "시작한 게임이 없다"와 "끝낸 게임이 없다(0%)"는 다른 말이다 (화면은 '—')
    """
    if whole == 0:
        return None
    # 0.1% 단위 정수로 반올림한 뒤 나눈다 ─ cost_per_hour와 같은 방법
    return (part * 1000 * 2 + whole) // (whole * 2) / 10
