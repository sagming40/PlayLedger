# PLAYLEDGER — DEVLOG

> **세션마다 겪은 일 · 막힌 일 · 배운 것**을 적는다. **최신이 위.** 지난 기록은 고치지 않고 위에 덧붙인다.
> 진행 상황 · 완료 기준은 [PLAN](PLAN.md), 결정의 이유는 [decisions/](decisions/README.md). 끝난 단계는 맨 아래 표에서 [archive/](archive/README.md)로.

## 현재 상태

| 항목 | 내용 |
|---|---|
| 단계 | **M3** ✅ 2026-11-04. 다음은 **M4** ⬜ 통계 대시보드 (`PLAN` M4) |
| 진행 중 | 없음 |
| 다음에 할 일 | **M4** 시작. 코드 쓰기 전에 "자동으로 할까, 직접 칠래?"를 먼저 묻는다. ECharts는 설치 전이라 의존성 목록을 먼저 보여 주고 사용자가 설치한다 |
| 판단이 남은 것 | 모바일 첫 줄이 요약 줄 도착 때 24px 밀리는 것. `가장 오래 방치` 요약(목업에 있고 `PLAN` 항목은 없음) ─ M4 방치 게임 추출 때 같이 본다 |
| M5 전에 | 라우터 `onError` 없음 ─ 화면 모듈을 못 받으면 안내 없이 빈 화면 ([DEVLOG_M2](archive/DEVLOG_M2.md) 2026-11-03 (7)). `npm audit` 19건 ─ `vite` · `vitest` · `source-map-js`는 고칠 버전이 있다. ESLint 계열은 `--force` 금지 ([DEVLOG_M3](archive/DEVLOG_M3.md) 2026-11-04 (4)) |
| 기기별로 할 일 | **집 PC(데스크톱 A)**: `git pull` → `web/`에서 `npm ci` (`motion-v` 추가). 마이그레이션 변화 없음. 확인은 `pytest`(65건) · `npm test`(151건). **노트북**: `git pull` → `docker compose up -d` → `server/`에서 `pip install -r requirements.txt` · `alembic upgrade head` → `server/.env`에 `STEAM_API_KEY` → `python -m app.scripts.sync_steam_apps` → `web/`에서 `npm ci` → 전역 설정(`~/.claude/CLAUDE.md`)에 "작업 방식" · "문서 체계" 절 추가 (원본은 회사 PC `~/.claude/CLAUDE.md`, 사본 `G:\내 드라이브\_private\.claude\desktop_cm_CLAUDE.md`). 선택: `git config blame.ignoreRevsFile .git-blame-ignore-revs` |
| 집 PC에만 있는 것 | 개발 DB의 확인용 계정 1개 · 기록 3개(Hollow Knight · 예시 게임 2개). 계정 값은 저장소에 없다(세션 임시 폴더). `.claude/launch.json`(Claude 앱 미리보기로 API · 프론트를 띄우는 설정)은 이 PC의 절대 경로가 들어 있어 커밋하지 않고 `.git/info/exclude`에 넣었다 ─ 다른 기기에서 Claude가 미리보기를 쓰려면 그 기기에서 새로 만든다 |
| 회사 PC에만 있는 것 | 화면 전후 픽셀 비교 스크립트는 저장소에 없다(세션 임시 폴더). 다른 기기에서 필요하면 방법을 보고 새로 만든다 ([DEVLOG_M2](archive/DEVLOG_M2.md) 2026-11-03 (6) · (7)) |

## 작성 규칙

- 형식은 전역 설정 "문서 체계" 절을 따른다: `## YYYY-MM-DD (n) · 제목 (기기)` → 한 일 / `[설계]` / 막힌 것(증상 · 원인 · 해결 · 배운 것) / 이번 세션 커밋 / 다음에 할 일. 2026-11-02 이전 블록은 옛 형식 그대로 둔다
- 기기 표기는 `README` 개발 환경 표를 따른다 (데스크톱 A · 데스크톱 B · 노트북)
- **막혔던 점은 해결됐어도 반드시 남긴다.** 같은 실수를 반복하지 않기 위한 기록이고, 나중에 이 프로젝트를 설명할 때 "어떤 문제를 어떻게 해결했는가"가 결과물보다 더 중요한 이야기가 된다
- 환경 버전은 여기 적지 않는다. `requirements.txt` · `package.json` · `ci.yml`이 원본이고, 기기별 런타임은 `README`에 있다

---

## 끝난 단계

단계가 끝나면 날짜 블록을 [archive/](archive/README.md)로 옮기고 여기에는 한 줄만 남긴다.

| 단계 | 기간 | 한 줄 요약 | 블록 |
|---|---|---|---|
| M3 상태 관리 + 평점 | 2026-11-03 ~ 11-04 | 상세 · 상태 · 평점 바로 고치기, 필터 · 주소 쿼리, 수정 · 삭제, 저장 알림, 수정 · 삭제 동시 실행 500 수정 | [DEVLOG_M3](archive/DEVLOG_M3.md) |
| M2 프론트 연동 · M2.5 Steam 검색 | 2026-09-28 ~ 11-03 | 로그인 · 목록 · 등록 · 설정 화면, 다크 · 라이트, Steam 검색 등록 · 커버, 상단 메뉴, ESLint · Prettier | [DEVLOG_M2](archive/DEVLOG_M2.md) |
| M1 백엔드 기초 | 2026-09-19 ~ 09-28 | 인증 · 보유 기록 CRUD · pytest 19건 · GitHub Actions · API 계약 문서 | [DEVLOG_M1](archive/DEVLOG_M1.md) |
| M0 환경 구성 | 2026-09-18 ~ 09-19 | 스택 전환 결정, Compose · FastAPI · Vue로 화면 → 서버 → DB 연결 | [DEVLOG_M0](archive/DEVLOG_M0.md) |
| v0 (옛 스택) | 2026-08-13 ~ 08-17 | RN + Django + MariaDB. 태그 `v0-rn-django` | [DEVLOG_v0](archive/DEVLOG_v0.md) |
