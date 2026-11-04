# app/core/rate_limit.py
"""요청 횟수 제한 ─ 비밀번호 대입과 가입 남용을 막는다 (PLAN M4.5)

서버 한 대 · 프로세스 하나 기준이라 메모리에 둔다. 재시작하면 지워지는데, 대입 공격을 늦추는 용도라 괜찮다
비유: 놀이기구 앞 번호표 기계. 최근 1분 동안 몇 장 뽑았는지만 세고, 다 차면 잠시 기다리라고 한다
"""

import time
from collections import deque


class RateLimiter:
    def __init__(self, limit: int, window_seconds: int, max_keys: int = 50_000):
        self.limit = limit
        self.window = window_seconds
        self.max_keys = max_keys   # 키를 바꿔 가며 메모리를 채우는 것도 막는다
        self._hits: dict[str, deque[float]] = {}

    def _alive(self, key: str, now: float) -> deque[float]:
        hits = self._hits.get(key)
        if hits is None:
            return deque()
        while hits and hits[0] <= now - self.window:
            hits.popleft()
        if not hits:
            del self._hits[key]
            return deque()
        return hits

    def retry_after(self, key: str) -> int:
        """지금 막혔으면 몇 초 뒤에 다시 올 수 있는지. 안 막혔으면 0"""
        now = time.monotonic()
        hits = self._alive(key, now)
        if len(hits) < self.limit:
            return 0
        return max(1, int(hits[0] + self.window - now) + 1)

    def hit(self, key: str) -> None:
        now = time.monotonic()
        hits = self._alive(key, now)
        if key not in self._hits:
            if len(self._hits) >= self.max_keys:
                self._evict(now)
            self._hits[key] = hits
        hits.append(now)

    def _evict(self, now: float) -> None:
        for key in list(self._hits):
            self._alive(key, now)
        # 그래도 가득이면 가장 먼저 들어온 키부터 버린다 ─ 정상 사용자를 막는 것보다 낫다
        while len(self._hits) >= self.max_keys:
            del self._hits[next(iter(self._hits))]

    def reset(self, key: str | None = None) -> None:
        if key is None:
            self._hits.clear()
        else:
            self._hits.pop(key, None)


# 같은 IP의 로그인 시도 전체 ─ 계정을 바꿔 가며 찔러도 걸린다
login_ip_limiter = RateLimiter(limit=30, window_seconds=60)
# 같은 IP + 같은 계정의 실패 ─ 성공하면 지운다. 계정만으로 세면 남이 일부러 틀려서 주인을 잠글 수 있다
login_failure_limiter = RateLimiter(limit=10, window_seconds=15 * 60)
# 가입 ─ 계정 만들기는 비싸고(해시) 자주 할 일이 아니다
register_limiter = RateLimiter(limit=10, window_seconds=60 * 60)
# 게임 등록 ─ Steam을 대신 불러 주는 경로라 사용자별로 제한한다
entry_create_limiter = RateLimiter(limit=60, window_seconds=60)

ALL_LIMITERS = (login_ip_limiter, login_failure_limiter, register_limiter, entry_create_limiter)
