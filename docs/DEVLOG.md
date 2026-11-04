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
| M5 전에 | 라우터 `onError` 없음 ─ 화면 모듈을 못 받으면 안내 없이 빈 화면 ([DEVLOG_M2](archive/DEVLOG_M2.md) 2026-11-03 (7)). `npm audit` 15건(moderate) ─ 전부 ESLint 계열의 `minimatch` 경유이고 호환되는 수정 버전이 아직 없다. M5 전에 다시 본다. `--force` 금지 (아래 2026-11-04 (5)) |
| 기기별로 할 일 | **집 PC(데스크톱 A)**: `git pull` → `web/`에서 `npm ci` (`motion-v` 추가, `vite` · `vitest` 올림). 마이그레이션 변화 없음. 확인은 `pytest`(65건) · `npm test`(151건). **노트북**: `git pull` → `docker compose up -d` → `server/`에서 `pip install -r requirements.txt` · `alembic upgrade head` → `server/.env`에 `STEAM_API_KEY` → `python -m app.scripts.sync_steam_apps` → `web/`에서 `npm ci` → 전역 설정(`~/.claude/CLAUDE.md`)에 "작업 방식" · "문서 체계" 절 추가 (원본은 회사 PC `~/.claude/CLAUDE.md`, 사본 `G:\내 드라이브\_private\.claude\desktop_cm_CLAUDE.md`). 선택: `git config blame.ignoreRevsFile .git-blame-ignore-revs` |
| 집 PC에만 있는 것 | 개발 DB의 확인용 계정 1개 · 기록 3개(Hollow Knight · 예시 게임 2개). 계정 값은 저장소에 없다(세션 임시 폴더). `.claude/launch.json`(Claude 앱 미리보기로 API · 프론트를 띄우는 설정)은 이 PC의 절대 경로가 들어 있어 커밋하지 않고 `.git/info/exclude`에 넣었다 ─ 다른 기기에서 Claude가 미리보기를 쓰려면 그 기기에서 새로 만든다 |
| 회사 PC에만 있는 것 | 화면 전후 픽셀 비교 스크립트는 저장소에 없다(세션 임시 폴더). 다른 기기에서 필요하면 방법을 보고 새로 만든다 ([DEVLOG_M2](archive/DEVLOG_M2.md) 2026-11-03 (6) · (7)) |

## 작성 규칙

- 형식은 전역 설정 "문서 체계" 절을 따른다: `## YYYY-MM-DD (n) · 제목 (기기)` → 한 일 / `[설계]` / 막힌 것(증상 · 원인 · 해결 · 배운 것) / 이번 세션 커밋 / 다음에 할 일. 2026-11-02 이전 블록은 옛 형식 그대로 둔다
- 기기 표기는 `README` 개발 환경 표를 따른다 (데스크톱 A · 데스크톱 B · 노트북)
- **막혔던 점은 해결됐어도 반드시 남긴다.** 같은 실수를 반복하지 않기 위한 기록이고, 나중에 이 프로젝트를 설명할 때 "어떤 문제를 어떻게 해결했는가"가 결과물보다 더 중요한 이야기가 된다
- 환경 버전은 여기 적지 않는다. `requirements.txt` · `package.json` · `ci.yml`이 원본이고, 기기별 런타임은 `README`에 있다

---

## 2026-11-04 (5) · `npm audit` 19건 → 15건 (데스크톱 B, 의존성 변경은 사용자가 침)

**한 일**
- `web/`에서 `npm audit fix` ─ `vite` 8.3.0 → 8.3.5, `vitest` · `@vitest/mocker` 5.0.2 → 5.1.0, `source-map-js` 1.2.1 → 1.2.2. 나머지는 따라 바뀐 것(`rolldown` 1.2.9 → 1.2.16, `postcss`, `obug` 2 → 3 등). 모두 `package.json` 범위 안이라 바뀐 파일은 `package-lock.json`뿐
- `npm audit`: 19건(moderate 17, high 2) → 15건(moderate 15, high 0)
- 확인: lint · format:check · `vue-tsc` 통과, `npm test` 151건 통과, `npm run build` 통과. 개발 서버 `vite` 8.3.5를 띄워 `/` 200, `/src/main.ts` 200, API를 안 띄운 `/api/x`는 프록시 오류 502(`ECONNREFUSED 8001`). 화면을 브라우저로 열어 보지는 않았다

**[설계] 남은 15건을 그대로 둔 이유**
- 15건이 모두 `minimatch` 경고 하나(GHSA-g3hv-75wg-m249, `<11.0.1`)에서 번진 것이다. `minimatch`는 10.2.6이 10.x의 마지막이라 11로 가야 하는데, 최신인 `eslint` 10.14.0(`^10.2.6`) · `@eslint/config-array` 0.23.5(`^10.2.4`) · `@typescript-eslint/typescript-estree` 8.72.1(`^10.2.2`)이 모두 10.x를 요구한다
- `npm audit fix --force`는 `eslint@4`로 내린다. `overrides`로 11을 강제하면 세 패키지가 선언한 범위를 벗어난다. 둘 다 하지 않는다. ESLint는 개발할 때만 돌고 빌드 결과물에 들어가지 않으므로 이 패키지들이 범위를 올릴 때를 기다린다

**막힌 것**
- 임시 폴더에서 `npm audit fix --package-lock-only`로 미리 뽑은 목록과 실제 결과가 조금 달랐다. 시험에서는 `@tailwindcss/oxide-wasm32-wasi` 아래 6개가 잠금 파일에 새로 적혔는데, 실제로 고칠 때는 적히지 않았다. 미리 뽑은 목록은 참고로만 보고 실제 잠금 파일을 다시 확인한다

**다음에 할 일**
- M5 전에 `npm audit`을 다시 돌려 `minimatch` 쪽이 풀렸는지 본다

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
