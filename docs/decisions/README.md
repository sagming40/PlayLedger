# decisions — 결정 기록

> **"왜 이렇게 정했나"를 남기는 결정 기록 묶음이다** — 결정 하나 = 파일 하나.
> 무엇을 만드는지는 [REQUIREMENTS](../REQUIREMENTS.md), 진행 상황은 [PLAN](../PLAN.md), 구현 중의 작은 판단은 [DEVLOG](../DEVLOG.md) `[설계]`. M1까지의 판단 기록은 [archive/](../archive/README.md) DEVLOG의 "결정 기록"에 그대로 있다.

- 파일 이름: `NNNN-영문-slug.md` (번호 4자리, 순서대로)
- 지난 결정은 고치지 않는다. 뒤집으면 **새 파일**을 만들고, 옛 파일의 상태만 `대체됨 → NNNN`으로 바꾼다
- 형식: 상태 · 날짜 / 맥락 / 결정 / 검토한 대안 / 감수할 것
- 0002 ~ 0006은 2026-11-02에 옛 문서 · DEVLOG에서 옮겨 적은 소급 기록이다 (0001 참고). 날짜는 결정한 날이다

| 번호 | 결정 | 상태 |
|---|---|---|
| [0001](0001-docs-refactor.md) | `docs/`를 전역 문서 체계로 재정비, API 명세를 ARCHITECTURE로 합침 | 채택 |
| [0002](0002-stack-switch.md) | RN + Django + MariaDB → Vue 3 + FastAPI + PostgreSQL, 앱 → 반응형 웹 | 채택 |
| [0003](0003-auth-jwt-refresh.md) | access는 JWT, refresh는 DB에 해시로 저장하는 무작위 문자열(rotation). 외부 로그인은 Discord | 채택 |
| [0004](0004-password-argon2.md) | 비밀번호 해싱은 argon2-cffi (Argon2id) | 채택 |
| [0005](0005-fixed-genres.md) | 장르는 Steam 공식 장르 8개 고정 목록 | 채택 |
| [0006](0006-main-only-branch.md) | 브랜치를 파지 않고 `main`에서만 작업 | 채택 |
| [0007](0007-steam-search-in-v1.md) | Steam 검색 등록과 커버 이미지를 v1.0에 넣는다 | 채택 |
| [0008](0008-steam-app-mirror.md) | Steam 게임 목록을 키로 받아 미러링하고 영어 제목으로 검색 | 채택 |
| [0009](0009-manual-steam-separate.md) | 수동 게임과 Steam 게임은 합치지 않고 별개 행 | 채택 |
| [0010](0010-top-nav.md) | 데스크톱 메뉴를 왼쪽 사이드바에서 상단 메뉴 띠로 | 채택 |
| [0011](0011-manual-games-per-user.md) | 직접 등록한 게임은 사용자별로 나누고 Steam 게임만 공유 | 채택 |
| [0012](0012-caddy-proxy.md) | 프록시는 Nginx 대신 Caddy | 채택 |
