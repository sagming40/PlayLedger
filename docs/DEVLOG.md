# PLAYLEDGER — DEVLOG

> **세션마다 겪은 일 · 막힌 일 · 배운 것**을 적는다. **최신이 위.** 지난 기록은 고치지 않고 위에 덧붙인다.
> 진행 상황 · 완료 기준은 [PLAN](PLAN.md), 결정의 이유는 [decisions/](decisions/README.md). 끝난 단계는 맨 아래 표에서 [archive/](archive/README.md)로.

## 현재 상태

| 항목 | 내용 |
|---|---|
| 단계 | **M4** ✅ 2026-11-04 (`v1.0.0` 태그는 아직 안 찍음). 다음은 **M5** ⬜ 배포 (`PLAN` M5) |
| 진행 중 | 없음 |
| 다음에 할 일 | `v1.0.0` 태그를 언제 찍을지 사용자에게 묻는다(사용자가 말하기 전에는 찍지 않는다). 그다음 **M5**. 코드 쓰기 전에 "자동으로 할까, 직접 칠래?"를 먼저 묻는다. 서버는 공용 인프라(전역 설정)를 먼저 본다 |
| 판단이 남은 것 | 모바일 첫 줄이 요약 줄 도착 때 24px 밀리는 것 |
| M5 전에 | 라우터 `onError` 없음 ─ 화면 모듈을 못 받으면 안내 없이 빈 화면 ([DEVLOG_M2](archive/DEVLOG_M2.md) 2026-11-03 (7)). `npm audit` 15건(moderate) ─ 전부 ESLint 계열의 `minimatch` 경유이고 호환되는 수정 버전이 아직 없다. M5 전에 다시 본다. `--force` 금지 ([DEVLOG_M4](archive/DEVLOG_M4.md) 2026-11-04 (5)) |
| 기기별로 할 일 | **집 PC(데스크톱 A)**: `git pull` → `web/`에서 `npm ci` (`motion-v` · `echarts` 추가, `vite` · `vitest` 올림). 마이그레이션 변화 없음. 확인은 `pytest`(90건) · `npm test`(163건). **노트북**: `git pull` → `docker compose up -d` → `server/`에서 `pip install -r requirements.txt` · `alembic upgrade head` → `server/.env`에 `STEAM_API_KEY` → `python -m app.scripts.sync_steam_apps` → `web/`에서 `npm ci` → 전역 설정(`~/.claude/CLAUDE.md`)에 "작업 방식" · "문서 체계" 절 추가 (원본은 회사 PC `~/.claude/CLAUDE.md`, 사본 `G:\내 드라이브\_private\.claude\desktop_cm_CLAUDE.md`). 선택: `git config blame.ignoreRevsFile .git-blame-ignore-revs` |
| 집 PC에만 있는 것 | 개발 DB의 확인용 계정 1개 · 기록 3개(Hollow Knight · 예시 게임 2개). 계정 값은 저장소에 없다(세션 임시 폴더). `.claude/launch.json`(Claude 앱 미리보기로 API · 프론트를 띄우는 설정)은 이 PC의 절대 경로가 들어 있어 커밋하지 않고 `.git/info/exclude`에 넣었다 ─ 다른 기기에서 Claude가 미리보기를 쓰려면 그 기기에서 새로 만든다 |
| 회사 PC에만 있는 것 | 화면 전후 픽셀 비교 스크립트는 저장소에 없다(세션 임시 폴더). 다른 기기에서 필요하면 방법을 보고 새로 만든다 ([DEVLOG_M2](archive/DEVLOG_M2.md) 2026-11-03 (6) · (7)) |

## 작성 규칙

- 형식은 전역 설정 "문서 체계" 절을 따른다: `## YYYY-MM-DD (n) · 제목 (기기)` → 한 일 / `[설계]` / 막힌 것(증상 · 원인 · 해결 · 배운 것) / 이번 세션 커밋 / 다음에 할 일. 2026-11-02 이전 블록은 옛 형식 그대로 둔다
- 기기 표기는 `README` 개발 환경 표를 따른다 (데스크톱 A · 데스크톱 B · 노트북)
- **막혔던 점은 해결됐어도 반드시 남긴다.** 같은 실수를 반복하지 않기 위한 기록이고, 나중에 이 프로젝트를 설명할 때 "어떤 문제를 어떻게 해결했는가"가 결과물보다 더 중요한 이야기가 된다
- 환경 버전은 여기 적지 않는다. `requirements.txt` · `package.json` · `ci.yml`이 원본이고, 기기별 런타임은 `README`에 있다

---

## 2026-11-04 (7) · VS Code 경고 88건 정리, 크기 클래스를 rem으로 (데스크톱 B, 자동 작업)

### 한 일
- 계기: Vue 확장을 깔자 `views/`에 경고 70건이 떴다. 출처는 Tailwind CSS IntelliSense의 `suggestCanonicalClasses`(표기 제안)다. 오류 0건, 빌드 · CI 영향 없음
- 같은 Tailwind 엔진(`canonicalizeCandidates`, 루트 16px)으로 `src` 전체를 세어 88건: `views` 70 + `components` 18. 파일별 수가 캡처와 일치. px → rem 77건, 표기만 다름 11건. 사용자가 전부 바꾸기로 정했다
- 진행 순서: 기준 화면 촬영(16 · 13px) → 엔진 결과로 일괄 변환 → 띠 규칙 정리 → 재촬영 · 비교 → 문서
- 메뉴 띠 글자 `PLAYLEDGER`의 `min-[760px]` 숨김을 없앴다. 띠 부품이 전부 rem이 되어 48rem에서 항상 들어간다
- 검증
  - 집계 88 → 0 (남은 `!m` 1건은 `entry-display.ts`의 `if (!m)`을 집계기가 잘못 센 것). VS Code 화면에서 0건인지는 사용자가 확인할 차례
  - `lint` · `format:check` · `vue-tsc` 통과, `npm test` 163 passed, `build` 통과
  - **16px 전후 픽셀 비교 48 / 48 동일** (1440 · 390px × 다크 · 라이트 × 목록, 등록, 평점 칸 + 입력 오류, 상세, ⋮ 메뉴, 삭제 대화상자, 수정, 통계, 더보기, 설정, 로그인, 가입). 같은 코드 2회 비교도 48 / 48
  - 13px(CSS로 재현) 1280 · 632 · 320px 36장 가로 넘침 0. 바꾸기 전 어긋나던 로고와 본문 왼쪽 끝이 맞음
  - 메뉴 띠(브라우저 기본 글꼴 재현): 13px · 폭 624, 633, 700 / 10px · 480 / 16px · 768 / 20px · 960 / 24px · 1152 모두 겹침 없음, 넘침 0
  - 확인용 계정 · 예시 게임 DB에서 삭제
- **확인 못 한 것**: 사용자의 회사 PC 크롬 실제 화면. 저장 알림은 촬영에 없다(클래스 값은 16px에서 같음). 글꼴이 작은 기기는 칸만 줄고 `text-[15px]` 같은 px 글자는 그대로라 빽빽해 보일 수 있다

### [설계]
- **전부 rem으로**: 기존에 `h-12`(rem)와 `h-[46px]`(px)가 섞여 글꼴이 16px이 아닌 브라우저에서 비율이 어긋났다. `max-w-[1200px]` + `px-10`처럼 로고와 본문 끝을 맞춘 계산도 깨졌다. 규칙은 `DESIGN` 2.2절
- **경고를 끄는 안은 버렸다**: 표기 11건만 고치고 끄면 지금 모양은 유지되지만 섞임이 남고 앞으로 새 코드도 안 잡힌다
- **`components/ui/`는 경고가 없어 건드리지 않았다**

### 막힌 것
- 증상: CSS로 `html { font-size: 13px }`를 넣고 폭 640을 쟀더니 메뉴 띠가 안 나왔다
  - 원인: 미디어 쿼리의 rem은 CSS가 아니라 브라우저 기본 글꼴 설정을 따른다. 이 재현으로는 48rem이 계속 768px이다
  - 해결: CDP `Page.setFontSizes`로 기본 글꼴을 바꿔 다시 쟀다
  - 배운 것: 글꼴 크기 재현은 html에 CSS를 넣는 것과 브라우저 설정을 바꾸는 것이 다르다
- 증상: 320px · 13px 상세에서 구매일이 `2025-09-` / `30`으로 꺾인다
  - 이번 변경 때문이 아니다. 바꾸기 전 사진도 같다. 작은 글꼴 · 좁은 폭의 극단 조합이라 그대로 뒀다

### 이번 세션 커밋
- `refactor(M5): Tailwind 클래스를 표준 표기로`, `fix(M5): 메뉴 띠 글자 숨김 규칙 제거`, `docs(M5): 경고 정리 기록`

### 다음에 할 일
- 회사 PC 크롬에서 화면 확인, VS Code 경고 0건 확인 → `v1.0.0` 태그 시점 → M5

---

## 끝난 단계

단계가 끝나면 날짜 블록을 [archive/](archive/README.md)로 옮기고 여기에는 한 줄만 남긴다.

| 단계 | 기간 | 한 줄 요약 | 블록 |
|---|---|---|---|
| M4 통계 대시보드 | 2026-11-04 | 통계 API · S-05 화면 · 예시 데이터 · 손계산 대조, `npm audit` 정리. `v1.0.0` 태그는 아직 | [DEVLOG_M4](archive/DEVLOG_M4.md) |
| M3 상태 관리 + 평점 | 2026-11-03 ~ 11-04 | 상세 · 상태 · 평점 바로 고치기, 필터 · 주소 쿼리, 수정 · 삭제, 저장 알림, 수정 · 삭제 동시 실행 500 수정 | [DEVLOG_M3](archive/DEVLOG_M3.md) |
| M2 프론트 연동 · M2.5 Steam 검색 | 2026-09-28 ~ 11-03 | 로그인 · 목록 · 등록 · 설정 화면, 다크 · 라이트, Steam 검색 등록 · 커버, 상단 메뉴, ESLint · Prettier | [DEVLOG_M2](archive/DEVLOG_M2.md) |
| M1 백엔드 기초 | 2026-09-19 ~ 09-28 | 인증 · 보유 기록 CRUD · pytest 19건 · GitHub Actions · API 계약 문서 | [DEVLOG_M1](archive/DEVLOG_M1.md) |
| M0 환경 구성 | 2026-09-18 ~ 09-19 | 스택 전환 결정, Compose · FastAPI · Vue로 화면 → 서버 → DB 연결 | [DEVLOG_M0](archive/DEVLOG_M0.md) |
| v0 (옛 스택) | 2026-08-13 ~ 08-17 | RN + Django + MariaDB. 태그 `v0-rn-django` | [DEVLOG_v0](archive/DEVLOG_v0.md) |
