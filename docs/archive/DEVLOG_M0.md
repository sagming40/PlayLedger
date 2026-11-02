# 개발 일지 — M0 · 환경 구성

> **M0 기간(2026-09-18 ~ 09-19 오후)의 DEVLOG 날짜 블록. 스택 전환 결정이 여기 있다**를 옮겨 둔 문서다. 보관만 하고 고치지 않는다. 옛 문서 이름(`ERD` · `UI_DESIGN` · `API_SPEC` · `MILESTONES` · `05_milestones` 등)은 당시 이름 그대로다 — 대응표는 [README](README.md).
> 지금 일지는 [../DEVLOG.md](../DEVLOG.md), 단계와 완료 기준은 [../PLAN.md](../PLAN.md).

---

## 2026-09-19(오전~오후/데스크톱 A) — M0 완료: FastAPI · Vue 구성 및 화면 → 서버 → DB 연결 확인

**관련 마일스톤**: M0 (환경 구성) → 완료

**한 일**

*서버*
- `server/` 가상환경 생성, FastAPI · Uvicorn 설치
- `app/main.py` 헬스체크 API (`GET /api/health`) — Swagger에서 200 확인
- `app/core/config.py` — pydantic-settings로 `.env` 로딩 (`DATABASE_URL` 필수값)
- `server/.env` / `.env.example` 분리
- `app/core/db.py` — SQLAlchemy async 엔진(커넥션 풀) 구성
- asyncio REPL에서 `SELECT version()`으로 컨테이너 DB 연결 실증 (PostgreSQL 18.6)
- Alembic async 템플릿 초기화, `env.py`에서 접속 주소를 `.env` 경유로 주입
- `requirements.txt` 생성

*프론트*
- `web/` Vite + Vue 3 + TypeScript 프로젝트 생성
- Vite `/api` 프록시 → FastAPI(8001) 연결, `App.vue`에서 헬스체크 응답 표시
- Tailwind CSS v4 플러그인 방식 적용 (`@tailwindcss/vite`)
- 경로 별칭 `@` → `src` 설정 (vite.config.ts + tsconfig 2종)
- shadcn-vue init (Reka UI · Lucide · Inter · Neutral) — 컴포넌트는 미추가
- Vite 템플릿 잔재 제거 (`HelloWorld.vue`, `src/assets/`)
- 루트 `.gitignore`에 web 규칙 통합, `.vscode/extensions.json`만 예외로 공유

**결정 기록**
- **API 서버 포트를 8001로 고정**
  8000은 다른 개인 프로젝트(콕)의 FastAPI와 겹칠 수 있음. DB 5434와 같은 원리로 프로젝트별 전용 번호를 배정해 두 프로젝트를 동시에 켜도 충돌하지 않게 함. MILESTONES 완료 기준의 포트 표기도 함께 수정
- **커밋 단위를 파일 단위 → 작업 파트 단위로 조정**
  M0 초반에는 파일 한두 개마다 커밋해 커밋 메시지 작성 시간이 코드 작성 시간을 넘어섰음. 기준을 지침의 *"이것만 따로 되돌리고 싶을 수 있는가?"* 로 되돌려 적용 — venv · FastAPI · 설정 · 엔진 · Alembic은 하나가 빠지면 나머지가 무의미하므로 한 덩어리. M1부터는 "완결된 동작"(회원가입, 로그인) 단위로 함
- **shadcn-vue는 init만 하고 컴포넌트는 받지 않음**
  shadcn-vue는 라이브러리 설치가 아니라 컴포넌트 소스를 프로젝트에 복사해 넣는 방식이라, 쓰지 않을 컴포넌트를 미리 받으면 그대로 죽은 코드가 됨. 필요한 것만 M2에서 받는다
- **빈 폴더 · 미사용 규칙을 선제적으로 만들지 않음**
  ARCHITECTURE 구조도에 있는 `core/`, `models/`, `schemas/` 등을 미리 만들지 않고 쓸 내용이 생길 때 생성. `.gitignore`에서도 사용하지 않는 규칙(`dist-ssr`, `.DS_Store`, macOS · Visual Studio 관련)을 제외

**막혔던 점 / 트러블슈팅**
- 증상: `uvicorn app.main:app --reload` 실행 시 `Error loading ASGI app. Could not import module "app.main"`. 포트 충돌로 의심해 `--port 8001`로 바꿨더니 동작해서 포트 문제로 오인
  - 원인: 실제로는 `main.py`가 아직 디스크에 저장되지 않은 상태였음. 로그를 보면 `Uvicorn running on http://127.0.0.1:8000`까지는 정상이었으므로 포트는 처음부터 문제가 아니었음
  - 해결: 파일 저장 후 정상 기동
  - 교훈: 에러 메시지가 말하는 것을 그대로 읽을 것. import 실패는 `Could not import module`, 포트 충돌은 `address already in use`로 각각 명시된다. 짐작으로 조건을 바꾸면 우연히 해결돼도 원인을 모른 채 넘어간다
- 증상: 설정 로딩 검증 중 `print(settings.database_url)`로 DB 비밀번호가 터미널에 원문 출력됨
  - 원인: 검증 목적에 필요한 것은 "값이 로딩됐는가"인데 값 전체를 출력하도록 명령을 구성함
  - 해결: 볼륨이 비어 있는 시점(테이블 0개)이라 손실 없이 비밀번호 교체 — 루트 `.env`와 `server/.env`를 함께 수정하고 `docker compose down -v` 후 재생성. 이후 검증은 `settings.database_url.split('@')[-1]`로 접속 주소만 출력
  - 교훈: 비밀값은 확인 과정에서도 원문을 노출하지 않는다. ARCHITECTURE 7장에 적어둔 "비밀번호를 바꿀 땐 두 파일을 함께 고친다" 규칙이 실제로 처음 적용된 사례이기도 하다
- 증상: `tsconfig.json`에 경로 별칭을 넣었는데 별칭이 동작하지 않을 상태였음 (커밋 전 검수에서 발견)
  - 원인: 키 이름을 `paths`가 아닌 `path`로 오타. TypeScript는 이를 에러로 알리지 않고 해당 설정이 없는 것처럼 동작함
  - 해결: 오타 수정
  - 교훈: v0의 `DEFAULT_AUTHENICATION_CLASSES` 오타와 같은 유형이다. 설정 키 오타는 "틀렸다"가 아니라 "없다"로 처리되어 조용히 넘어간다. 반대로 `config.py`에서 `DATABASE_URL`이 없으면 서버가 즉시 멈추게 만든 것이 이 유형에 대한 대비책
- 증상: `tsconfig.app.json`에 `baseUrl`을 넣자 Problems에 deprecated 에러
  - 원인: TypeScript 6부터 `baseUrl`이 폐기 예정. shadcn-vue 문서는 이전 버전 기준으로 작성돼 있었음
  - 해결: `baseUrl` 제거. TypeScript 4.4부터 `paths`는 `baseUrl` 없이 tsconfig 파일 위치 기준으로 해석되며, 값을 `"./src/*"` 형태로 써 두었으므로 그대로 동작
  - 교훈: 공식 문서라도 내가 쓰는 버전과 다를 수 있다. 버전을 먼저 확인하고 대조할 것

**발견 사항 (지금 조치하지 않음)**
- 브라우저 쿠키는 포트를 구분하지 않는다. v0 Django가 `localhost`에 심은 `csrftoken`이 5173 요청에도 딸려오는 것을 Network 탭에서 확인. M2에서 refresh 토큰 쿠키를 도입할 때 같은 `localhost`를 쓰는 다른 프로젝트와 서로 덮어쓸 수 있으므로, 쿠키 이름에 프로젝트 접두사를 붙여 대비할 것
- shadcn-vue init이 Inter 폰트를 구글 서버에서 받아오는 방식으로 `style.css`에 추가함. M5 배포 시 프로젝트 내장 여부를 검토 (MILESTONES M5에 항목 추가)

**다음에 할 일**
- M0 PR 생성 후 `main`에 병합 (M0는 CI 없음), `m1-backend` 브랜치 생성
- M1 착수: v1.0 범위 모델 정의(`users`, `refresh_tokens`, `games`, `genres`, `game_genres`, `entries`) → 첫 마이그레이션을 `--sql`로 확인

---

## 2026-09-18(저녁~밤/데스크톱 A) — M0 진행 중: 공통 설정 및 PostgreSQL 컨테이너 구성

**관련 마일스톤**: M0 (환경 구성) → 진행 중

**한 일**
- `m0-setup` 브랜치 생성 (브랜치 전략 전환 첫 적용)
- `.gitignore`를 새 스택 기준으로 재작성 — 비밀값 · Python · Node · 로그 · OS 구역으로 분리
- `.gitattributes` 추가 — `* text=auto eol=lf`로 줄바꿈 규칙을 저장소 차원에서 고정
- `docker-compose.yml` 작성 — `postgres:18`, 이름 붙은 볼륨, healthcheck, `127.0.0.1` 바인딩
- 루트 `.env` / `.env.example` 분리 (Compose용 DB 계정)
- HeidiSQL로 컨테이너 접속 확인, `SHOW data_directory`로 "컨테이너 DB에 붙었다"까지 검증
- ARCHITECTURE v1.1 개정 — 루트 `.env` 추가, 구조도에 `.gitattributes` 반영, Redis 도입 시점 표기 수정

**결정 기록**
- **Compose용 DB 계정을 루트 `.env`로 분리**
  Docker Compose는 compose 파일과 같은 폴더의 `.env`를 자동으로 읽는다. `server/.env`를 `env_file`로 통째로 넘기면 DB 컨테이너가 쓰지도 않는 JWT 서명 키 · Steam API 키까지 받게 되므로, DB 계정만 루트 `.env`로 분리. 대신 같은 비밀번호가 두 파일에 존재하므로 "바꿀 땐 함께 고친다"를 ARCHITECTURE 7장에 규칙으로 명시
- **호스트 포트를 5434로 고정**
  5432는 Windows에 설치된 PostgreSQL 18 서비스, 5433은 다른 개인 프로젝트(콕) 컨테이너가 사용 중. 포트를 비켜 앉는 대신 프로젝트별 전용 번호를 배정해, 데스크톱 B를 포함한 어느 환경에서도 같은 설정이 동작하도록 함
- **`postgres:18` 볼륨 경로를 `/var/lib/postgresql`로 지정**
  인터넷 예제 다수가 쓰는 `/var/lib/postgresql/data`는 17 이하 기준. 18 이미지는 데이터 폴더가 버전별 하위 경로(`/18/docker`)로 바뀌어, 예제대로 두면 데이터가 볼륨 바깥에 저장되고 컨테이너 삭제 시 조용히 사라진다. `SHOW data_directory` 결과가 볼륨 안쪽임을 확인

**막혔던 점 / 트러블슈팅**
- 증상: `git check-ignore -v server/.env.example`이 "출력 없음"을 예상했는데 `.gitignore:12:!.env.example` 한 줄이 출력됨
  - 원인: `-v` 옵션은 "무시 여부"가 아니라 "마지막으로 일치한 규칙"을 보여준다. `!` 예외 규칙에 걸려도 그 줄을 출력한다
  - 해결: 규칙 앞의 `!`를 확인해 "무시 대상에서 제외됨"으로 해석. `-v` 없이 실행하면 최종적으로 무시되는 경로만 출력되고, 종료 코드 `1`이면 무시되지 않음
  - 교훈: 도구의 출력이 예상과 다를 때, 도구가 무엇을 보여주기로 되어 있는지부터 확인할 것
- 증상: `.gitattributes` 적용 후 `.gitignore`와 `03_erd.md`가 `git status`에 modified로 표시되는데 `git diff`는 아무것도 출력하지 않음
  - 원인: Git은 속도를 위해 인덱스에 파일 크기·수정 시각을 캐시해 두고 그것만 비교한다. CRLF → LF 변환으로 크기와 시각이 바뀌어 캐시와 어긋났을 뿐, 내용은 저장소와 동일했음
  - 해결: `git add --renormalize .`로 인덱스를 새 규칙 기준으로 재작성. 두 파일이 목록에서 사라짐
  - 교훈: `git status`의 modified는 "바뀐 것 같다"이고, "실제로 무엇이 바뀌었는가"는 `git diff`가 답한다. 원인을 확인하기 전에 `git add .`를 하면 정체 모를 변경이 커밋에 섞인다
- 증상: VS Code에서 새로 만든 파일(`.gitignore`, `docker-compose.yml`, `.env`)이 계속 CRLF로 저장됨
  - 원인: `Files: Eol` 기본값이 `auto`라 Windows 기본값(CRLF)을 따름
  - 해결: 사용자 설정을 `\n`으로 변경. Git 추적 대상은 `.gitattributes`가 커밋 시 정리하지만, `.env`는 추적 대상이 아니라 `.gitattributes`가 관여하지 않으므로 편집기 설정이 유일한 방어선
  - 교훈: `.env` 값 끝에 보이지 않는 `\r`이 붙으면 비밀번호가 맞는데도 접속이 실패할 수 있다. 컨테이너를 만들기 전에 정리해 둘 것

**다음에 할 일**
- 서버 파트 착수: `server/` 가상환경 → FastAPI 헬스체크 → `.env` 설정 로딩 → SQLAlchemy 엔진 → Alembic
- 이어서 프론트 파트: Vite 프로젝트 → Tailwind → 프록시 연결

---

## 2026-09-18(오후~저녁/데스크톱 A) — M0 재착수: 스택 전환 결정 및 설계 문서 전면 개정

**관련 마일스톤**: M0 (환경 구성) → 진행 중

**한 일**
- 기존 구현(M1 완료, M2 네비게이션 골격)을 `v0-rn-django` 태그로 보존
- 구 스택 코드(`app/`, `server/`) 제거 및 빌드 찌꺼기 정리
- 설계 문서 전면 개정 (01 ~ 05, `README`)
  - `ERD.md` → `03_erd.md`로 파일명 변경 (`git mv`로 이력 유지)
  - 구조도 · 인증 · 동기화 · 화면 흐름을 mermaid로 전환
  - `REQUIREMENTS`에 유즈케이스, `UI_DESIGN`에 화면 흐름 · 상태 전환 · 시퀀스 다이어그램 추가
- 마일스톤을 M0 ~ M11, 버전별(v1.0 ~ v2.1)로 재구성

**결정 기록**
- **스택 전환 (RN + Django + MariaDB → Vue 3 + FastAPI + PostgreSQL)**
  취업으로 프로젝트 목적이 포트폴리오 → 자기계발 · 취미로 바뀜. 함께 준비하던 별도 프로젝트(단축 URL 서비스 '콕')는 기술 스택을 먼저 정하고 주제를 끼워 맞춘 탓에 재미가 없어 접고, 그 스택을 문제의식이 분명한 PlayLedger에 적용. 전환 시점의 구현량이 M1 + 네비게이션 골격이라 버리는 비용이 작았음. 기술별 근거는 `02_architecture.md` 3장
- **모바일 앱 → 반응형 웹**
  v0의 "PC 앞이 아닐 때" 시나리오를 다시 따져보니, 기록과 분석이 실제로 일어나는 순간은 Steam을 켜둔 PC 앞이 더 많음. 모바일은 반응형으로 대응 (`REQUIREMENTS` 3.2절에서 "웹 제외"를 반전)
- **범위 확대 + 버전별 결승선**
  시간 여유가 생겨 위시리스트 · 구매 전 경고 · Steam 자동 동기화 · 플레이 세션 · 추첨 · Discord 로그인을 범위에 넣음. 대신 마감이 없어진 만큼 "끝이 없어 못 끝내는" 위험을 막으려고 v1.0은 기존 범위(M0 ~ M4) 그대로 두고, 확장은 v1.1 ~ v2.1로 버전을 나눠 결승선을 여러 개 둠
- **소셜 로그인은 Discord (OAuth 2.0)**
  Steam 로그인은 OAuth가 아닌 OpenID 2.0이라 학습 목표(OAuth 2.0)와 맞지 않음. GitHub보다 게이머에게 자연스러운 Discord 선택. Steam은 로그인이 아닌 라이브러리 연결 용도로 유지
- **데이터 모델 주요 변경** — 상세는 `03_erd.md`
  플레이타임을 분 단위 정수로(세션 증가분 계산 시 반올림 오차 방지), 위시리스트를 별도 테이블로(통계 쿼리 제외 조건 누락 방지), refresh 토큰은 해시로 저장
- **F-02에서 플랫폼 · 구매처 제외**
  v0부터 요구사항에는 있었지만 데이터 모델에 컬럼이 없었고, 이를 쓰는 통계도 없었음. F-26으로 이관
- **Git 전략 전환 (main 직접 커밋 → 마일스톤 단위 브랜치 + PR)**
  목적이 자기계발로 바뀌면서 실무 흐름(브랜치 → PR → CI 확인 → 병합)을 익히는 것 자체가 목표가 됨. M1부터 GitHub Actions가 붙어 병합 전 검증이 가능해지고, 브랜치 조작이 마일스톤당 1회라 오버헤드가 작음. 브랜치가 굵은 대신 되돌리기 단위는 잘게 나눈 커밋이 맡고, 그 커밋 분리가 사라지지 않도록 병합은 Squash가 아닌 일반 Merge로 함. M0는 CI가 없으므로 M0 PR은 Actions 확인 없이 병합

**막혔던 점 / 트러블슈팅**
- 증상: `git rm -r app server` 커밋 후 GitHub Desktop에 `app/android/app/.cxx/...` 빌드 파일 425개가 새 파일로 표시됨
  - 원인: RN CLI가 만든 하위 `.gitignore`(`app/.gitignore`)도 함께 삭제됨. `.cxx`, `build` 같은 안드로이드 빌드 폴더를 무시하는 규칙이 그 파일에만 있었는데, 규칙이 사라지면서 가려져 있던 파일들이 untracked로 드러남. 루트 `.gitignore`엔 공통 규칙만 있어서 막지 못함
  - 해결: 425개를 커밋하지 않고, VS Code를 종료한 뒤(Java 확장이 Gradle로 파일을 잡고 있음) `app/`, `server/` 폴더를 탐색기에서 통째로 삭제
  - 교훈: `.gitignore`는 폴더마다 따로 있을 수 있고, `git rm`은 그 파일도 디스크에서 지운다. 폴더를 정리할 땐 커밋 직후 `git status`로 갑자기 늘어난 파일이 없는지 확인할 것. 무시되던 파일 목록은 `git status --ignored`로 미리 볼 수 있다
- 증상: 문서 검수 중 문서끼리 서로 다른 말을 하는 곳이 여러 번 발견됨 (R-02 "자동 폴링 안 함" vs F-19 자동 동기화, ARCHITECTURE 안에서 Redis 도입 시점 M8 vs M9, v0부터 있던 F-02 플랫폼 항목 vs ERD)
  - 원인: 문서 여러 개를 한 번에 개정하면서, 같은 사실을 다른 문서에서도 말하고 있는지 대조하지 않음
  - 해결: 커밋 전 검수 단계에서 하나씩 정정
  - 교훈: 설정을 바꾸면 그 값을 참조하는 곳을 검색하듯, 문서도 바꾼 내용의 핵심어(예: "자동 동기화", "Redis")로 `docs/` 전체를 검색해 어긋난 곳이 없는지 확인할 것
- 증상: ARCHITECTURE의 Discord 로그인 시퀀스와 비밀번호 해시 비교 위치가 실제로는 틀린 흐름이었음 (mermaid는 문법 오류 없이 그림이 잘 그려짐)
  - 원인: 콜백은 fetch 응답이 아니라 브라우저 페이지 이동이라 access 토큰을 응답 본문으로 받을 수 없음. 해시 비교는 DB가 아니라 서버가 함
  - 해결: 콜백에서는 refresh 쿠키만 심고 프론트가 재발급 API로 access 토큰을 받는 흐름으로 수정
  - 교훈: M1 때 "서버가 에러 없이 뜬다고 코드가 의도대로 동작하는 건 아니다"와 같다. **다이어그램이 그려진다고 흐름이 맞는 건 아니다.** 그림도 코드처럼 흐름을 따라가며 검수해야 한다
- 증상: ERD 변경 이력의 v0.2 줄이 `(기존 내용 유지)`라는 자리표시로 덮여 커밋 직전까지 감
  - 원인: 안내받은 블록 안의 자리표시를 그대로 옮겨 적음
  - 해결: 검수 단계에서 발견해 원문 복구
  - 교훈: 문서를 크게 고친 뒤엔 커밋 전에 `git diff`로 **삭제된 줄(`-`)** 을 한 번 훑어볼 것. 의도하지 않은 삭제는 추가된 줄보다 삭제된 줄에서 잘 보인다
- 증상: ERD만 줄바꿈 형식이 CRLF(나머지는 LF)
  - 원인: VS Code에서 새로 만든 파일이 Windows 기본값을 따름
  - 해결: 보류 (Git이 커밋 시 변환). M0에서 `.gitattributes`로 근본 해결 예정

**다음에 할 일**
- M0 착수: `.gitignore` 재작성 → `.gitattributes` → Docker Compose(PostgreSQL) → FastAPI 헬스체크 → Vite 프로젝트 → 프록시 연결
- Project Instructions의 구 스택 표현 갱신 (파일명, 폴더 구조, 스택명)

---

