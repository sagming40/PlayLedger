"""S-05 통계 ─ REQUIREMENTS 5장의 계산식과 DESIGN 3.5절.

기대값은 코드로 계산하지 않고 예시 26개(app/scripts/seed_demo.py)를 손으로 계산해 적었다.
서버와 같은 식으로 기대값을 만들면 식이 틀려도 테스트가 통과한다.
"""

import asyncio
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.metrics import percent
from app.models.user import User
from app.scripts.seed_demo import DEMO, add_demo_entries
from app.services.stats import LIST_LIMIT, effective_today

A_EMAIL = "alice@example.com"
B_EMAIL = "bob@example.com"


async def seeded(client, auth_headers, session_factory, email=A_EMAIL):
    """예시 26개를 넣은 계정의 출입증과 오늘 날짜"""
    headers = await auth_headers(email)
    today = datetime.now(timezone.utc).date()
    async with session_factory() as db:
        user_id = await db.scalar(select(User.id).where(User.email == email))
        await add_demo_entries(db, user_id=user_id, today=today)
        await db.commit()
    return headers, today


async def get_stats(client, headers, **params):
    res = await client.get("/api/stats", headers=headers, params=params)
    assert res.status_code == 200, res.text
    return res.json()


async def create_entry(client, headers, title, **fields):
    res = await client.post("/api/entries", json={"title": title, "status": "BACKLOG", **fields}, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


# ── 계산식 ──────────────────────────────────────────────


@pytest.mark.parametrize(
    ("part", "whole", "expected"),
    [
        (11, 26, 42.3),  # 42.307…
        (6, 18, 33.3),  # 33.33…
        (2, 3, 66.7),  # 66.66…
        (1, 8, 12.5),
        (1, 2000, 0.1),  # 0.05% ─ 0.5 경계는 올림
        (0, 5, 0.0),  # 끝낸 게임이 없음 ─ 계산할 수 있고 0이다
        (5, 5, 100.0),
        (0, 0, None),  # 시작한 게임이 없음 ─ 계산할 수 없다
    ],
)
def test_percent(part, whole, expected):
    assert percent(part, whole) == expected


def test_today_uses_browser_date_within_a_day():
    """한국 2026-11-04 08:00 = UTC 11-03 23:00 ─ 서버 날짜로 세면 방치일수가 하루 모자란다"""
    now = datetime(2026, 11, 3, 23, 0, tzinfo=timezone.utc)
    assert effective_today(date(2026, 11, 4), now) == date(2026, 11, 4)
    assert effective_today(date(2026, 11, 2), now) == date(2026, 11, 2)
    # 이틀 이상 차이 ─ PC 시계가 틀렸다. 에러로 막지 않고 서버 날짜
    assert effective_today(date(2026, 11, 5), now) == date(2026, 11, 3)
    assert effective_today(date(2020, 1, 1), now) == date(2026, 11, 3)
    assert effective_today(None, now) == date(2026, 11, 3)


# ── 예시 26개 ─ 손으로 계산한 값 (PLAN M4 완료 기준) ──────


def test_demo_has_at_least_20_games():
    assert len(DEMO) == 26


async def test_cards(client, auth_headers, session_factory):
    headers, today = await seeded(client, auth_headers, session_factory)
    stats = await get_stats(client, headers, today=str(today))
    assert stats["total"] == 26
    assert stats["backlog"] == 8
    # 1시간 미만 11개 ─ 미시작 8개(0분 7개 + 30분) + 59분 + 45분 + 0분. 60분은 세지 않는다
    assert stats["abandoned_rate"] == 42.3
    # 클리어 6 ÷ (26 - 미시작 8)
    assert stats["completion_rate"] == 33.3


async def test_longest_idle(client, auth_headers, session_factory):
    headers, today = await seeded(client, auth_headers, session_factory)
    stats = await get_stats(client, headers, today=str(today))
    assert [(g["title"], g["idle_days"]) for g in stats["longest_idle"]] == [
        ("[예시] 별빛 왕국", 214),
        ("[예시] 강철 항해", 180),
        ("[예시] 깊은 동굴 탐험", 179),
        ("[예시] 도시 설계사", 92),
        ("[예시] 달빛 정원", 41),
        ("[예시] 잠깐 켜 본 게임", 14),
        ("[예시] 오늘 산 퍼즐", 0),
        # 구매일 모르는 미시작은 셀 수 없어 없다. 미시작이 아니면 오래됐어도 없다
    ]


async def test_highest_cost(client, auth_headers, session_factory):
    headers, today = await seeded(client, auth_headers, session_factory)
    stats = await get_stats(client, headers, today=str(today))
    assert [(g["title"], g["cost_per_hour"]) for g in stats["highest_cost"]] == [
        ("[예시] 서킷 챔피언", 71186),  # 70000 ÷ (59/60) = 71186.44
        ("[예시] 축구 감독 시즌", 55000),  # 동점이면 먼저 등록한 것부터
        ("[예시] 드리프트 왕", 55000),  # 66000 ÷ 1.2
        ("[예시] 잠깐 켜 본 게임", 40000),
        ("[예시] 전술 함대", 22500),
        ("[예시] 어둠의 탑", 13000),
        ("[예시] 문명의 새벽", 7500),
        ("[예시] 짧은 엔딩", 6667),  # 5000 ÷ 0.75 = 6666.67
        ("[예시] 붉은 사막 횡단", 5280),
        ("[예시] 바람의 모험", 1650),
        ("[예시] 은하 전략 사령부", 1581),  # 1580.65
        ("[예시] 숲속 기사단", 1440),
        ("[예시] 눈 덮인 산 오르기", 1202),  # 1202.19
        ("[예시] 황금 도시", 1058),  # 1057.69
        ("[예시] 장르 없는 게임", 1000),
        ("[예시] 작은 농장 일기", 395),  # 395.06
        ("[예시] 무료 전투장", 0),  # 무료는 계산할 수 있고 0이다
        # 플레이타임 0(미시작 7개 · 농구 스타), 구매가 모름은 값이 없어 없다
    ]


async def test_genres(client, auth_headers, session_factory):
    headers, today = await seeded(client, auth_headers, session_factory)
    stats = await get_stats(client, headers, today=str(today))
    assert [
        (g["name"], g["total"], g["started"], g["cleared"], g["completion_rate"], g["avg_playtime_minutes"]) for g in stats["genres"]
    ] == [
        ("캐주얼", 5, 3, 2, 66.7, 1191),  # (2430 + 1098 + 45) ÷ 3
        ("어드벤처", 4, 3, 2, 66.7, 900),  # (750 + 750 + 1200) ÷ 3
        ("액션", 8, 6, 3, 50.0, 1197),  # (750 + 600 + 3744 + 750 + 1098 + 240) ÷ 6
        ("RPG", 6, 4, 2, 50.0, 1371),  # (300 + 3744 + 1200 + 240) ÷ 4
        ("전략", 4, 3, 1, 33.3, 820),  # (1860 + 480 + 120) ÷ 3
        ("시뮬레이션", 3, 2, 0, 0.0, 1275),  # (2430 + 120) ÷ 2
        ("레이싱", 2, 2, 0, 0.0, 66),  # (59 + 72) ÷ 2 = 65.5 → 올림
        ("스포츠", 2, 2, 0, 0.0, 30),  # (60 + 0) ÷ 2
    ]


# ── 빈 값 · 경계 ────────────────────────────────────────


async def test_no_games(client, auth_headers):
    """게임 0개 ─ 오류 없이 빈 값 (PLAN M4 완료 기준)"""
    stats = await get_stats(client, await auth_headers(A_EMAIL))
    assert stats == {
        "total": 0,
        "backlog": 0,
        "abandoned_rate": None,
        "completion_rate": None,
        "longest_idle": [],
        "highest_cost": [],
        "genres": [],
    }


async def test_only_backlog(client, auth_headers):
    """전부 미시작 ─ 완주율은 0%가 아니라 없음. 장르도 같다"""
    headers = await auth_headers(A_EMAIL)
    await create_entry(client, headers, "Hollow Knight", genre_ids=[1])
    stats = await get_stats(client, headers)
    assert stats["completion_rate"] is None
    assert stats["abandoned_rate"] == 100.0
    assert stats["genres"][0]["started"] == 0
    assert stats["genres"][0]["completion_rate"] is None
    assert stats["genres"][0]["avg_playtime_minutes"] is None


async def test_genre_without_started_game_goes_last(client, auth_headers):
    headers = await auth_headers(A_EMAIL)
    await create_entry(client, headers, "미시작 게임", genre_ids=[1])
    await create_entry(client, headers, "포기한 게임", status="DROPPED", genre_ids=[2])
    stats = await get_stats(client, headers)
    assert [(g["genre_id"], g["completion_rate"]) for g in stats["genres"]] == [(2, 0.0), (1, None)]


async def test_future_purchase_counts_as_zero_days(client, auth_headers):
    """미래 날짜(입력 실수)는 0일 ─ 목록 카드와 같은 규칙"""
    headers = await auth_headers(A_EMAIL)
    today = datetime.now(timezone.utc).date()
    await create_entry(client, headers, "미래 구매", purchased_at=str(today + timedelta(days=30)))
    stats = await get_stats(client, headers, today=str(today))
    assert stats["longest_idle"][0]["idle_days"] == 0


async def test_browser_today_changes_idle_days(client, auth_headers):
    headers = await auth_headers(A_EMAIL)
    today = datetime.now(timezone.utc).date()
    await create_entry(client, headers, "방치 게임", purchased_at=str(today - timedelta(days=10)))
    assert (await get_stats(client, headers, today=str(today + timedelta(days=1))))["longest_idle"][0]["idle_days"] == 11


async def test_invalid_today_is_422(client, auth_headers):
    headers = await auth_headers(A_EMAIL)
    res = await client.get("/api/stats", headers=headers, params={"today": "내일"})
    assert res.status_code == 422


async def test_huge_price_does_not_overflow(client, auth_headers):
    """integer 최댓값 구매가 ─ SQL에서 곱할 때 넘치면 500이 난다"""
    headers = await auth_headers(A_EMAIL)
    await create_entry(client, headers, "아주 비싼 게임", purchase_price=2_147_483_647, playtime_minutes=60, status="PLAYING")
    stats = await get_stats(client, headers)
    assert stats["highest_cost"][0]["cost_per_hour"] == 2_147_483_647


async def test_lists_are_capped(client, auth_headers):
    headers = await auth_headers(A_EMAIL)
    today = datetime.now(timezone.utc).date()
    for i in range(LIST_LIMIT + 1):
        await create_entry(client, headers, f"방치 {i}", purchased_at=str(today - timedelta(days=i)), purchase_price=1000)
        await create_entry(client, headers, f"비용 {i}", status="PLAYING", purchase_price=1000 + i, playtime_minutes=60)
    stats = await get_stats(client, headers, today=str(today))
    assert len(stats["longest_idle"]) == LIST_LIMIT
    assert stats["longest_idle"][0]["idle_days"] == LIST_LIMIT
    assert len(stats["highest_cost"]) == LIST_LIMIT
    assert stats["highest_cost"][0]["cost_per_hour"] == 1000 + LIST_LIMIT


# ── 남의 데이터 · 동시 실행 ─────────────────────────────


async def test_requires_login(client):
    assert (await client.get("/api/stats")).status_code == 401


async def test_other_users_entries_are_not_counted(client, auth_headers, session_factory):
    """같은 제목을 둘이 가져도 숫자와 장르는 각자의 것이다"""
    await seeded(client, auth_headers, session_factory, email=A_EMAIL)
    b = await auth_headers(B_EMAIL)
    entry = await create_entry(
        client, b, "[예시] 황금 도시", status="DROPPED", purchase_price=1, playtime_minutes=60, genre_ids=[1]
    )
    stats = await get_stats(client, b)
    assert stats["total"] == 1
    assert stats["backlog"] == 0
    assert stats["completion_rate"] == 0.0
    assert stats["longest_idle"] == []
    assert [g["entry_id"] for g in stats["highest_cost"]] == [entry["id"]]
    # A가 붙인 장르가 B에게 따라오지 않는다
    assert {g["name"]: g["total"] for g in stats["genres"]} == {"액션": 1}


async def test_stats_survive_concurrent_delete(client, auth_headers, session_factory):
    """통계를 읽는 사이 기록이 지워져도 500이 나지 않는다 ─ 읽기만 해서 잠금이 없다"""
    headers, today = await seeded(client, auth_headers, session_factory)
    entries = (await client.get("/api/entries", headers=headers, params={"limit": 100})).json()["items"]
    results = await asyncio.gather(
        *[client.delete(f"/api/entries/{e['id']}", headers=headers) for e in entries[:10]],
        *[client.get("/api/stats", headers=headers, params={"today": str(today)}) for _ in range(5)],
    )
    assert [r.status_code for r in results[:10]] == [204] * 10
    assert [r.status_code for r in results[10:]] == [200] * 5
    assert (await get_stats(client, headers, today=str(today)))["total"] == 16
