# PlayLedger — DEVLOG

> 세션별 개발 회고 및 트러블슈팅 기록

이 문서는 마일스톤 문서(`05_milestones.md`)처럼 "계획"을 담는 곳이 아니라,
**실제로 각 세션에서 무슨 일이 있었는지**를 기록하는 곳이다.
막혔던 지점, 해결한 방법, 다음에 참고할 만한 실수 등을 가감 없이 남긴다.

---

## 현재 상태

**진행 중** · M1 (백엔드 기초) — 모델 6종 · 첫 마이그레이션 · 회원가입 API 완료. 로그인 · CRUD · 테스트 · 장르 시드 남음

**환경 요약**
| 항목 | 값 |
|---|---|
| Python | 3.13.5 |
| Node.js | v24.15.0 |
| FastAPI · Uvicorn | 0.141.1 · 0.53.0 |
| SQLAlchemy · asyncpg | 2.0.54 · 0.31.0 |
| Alembic | 1.20.0 (async 템플릿, 마이그레이션 1건 적용) |
| argon2-cffi | 25.1.0 (Argon2id, 비밀번호 해싱) |
| Vue · Vite · TypeScript | 3.5.42 · 8.3.0 · 6.0.2 |
| Tailwind CSS · shadcn-vue | 4.3.3 · 2.8.2 (컴포넌트 미추가) |
| PostgreSQL | 18.6 (`postgres:18` 컨테이너, 테이블 7개 — v1.0 범위 6종 + `alembic_version`) |
| Docker · Compose | 29.8.0 · v5.5.1 |
| 포트 | DB `5434` · API `8001` · 프론트 `5173` |
| 이전 버전 | `v0-rn-django` 태그 (RN 0.87.0 + Django 6.1 + MariaDB 12.2.2) |
| 대상 | 웹 (데스크톱 · 모바일 브라우저) |

**실행 방법** · 터미널 3개 — 프로젝트 루트에서 `docker compose up -d` / `server`에서 `uvicorn app.main:app --reload --port 8001` / `web`에서 `npm run dev`

**다음에 할 일** · 로그인(access 토큰 + refresh 쿠키) → 토큰 재발급(rotation) → 로그아웃 → `get_current_user` 의존성

---

## 작성 규칙

- 세션(하루 작업 단위) 종료 시 또는 마일스톤 완료 시 기록
- 최신 항목이 위로 오도록 역순 정렬
- 형식: 날짜 / 관련 마일스톤 / 한 일 / 결정 기록 / 막혔던 점 / 다음에 할 일 (결정 기록은 판단이 있었던 세션만)

**막혔던 점은 해결됐어도 반드시 남긴다.** 같은 실수를 반복하지 않기 위한
기록이기도 하고, 나중에 이 프로젝트를 설명할 때 "어떤 문제를 어떻게
해결했는가"가 결과물보다 더 중요한 이야기가 되기 때문이다.

---

## 기록 템플릿

```markdown
## YYYY-MM-DD — 한 줄 요약

**관련 마일스톤**: MX (단계명) → 진행 중 / 완료

**한 일**
-

**결정 기록** (선택 — 판단 근거를 남길 게 있을 때)
- **결정 내용**
  왜 그렇게 했는지

**막혔던 점 / 트러블슈팅**
- 증상:
- 원인:
- 해결:
- 교훈:

**다음에 할 일**
-
```

---
 
<!-- 새 기록은 이 아래에 추가한다 (최신이 위로) -->

## 2026-09-20(9/19 저녁 ~ 9/20 오전/노트북) — M1 진행 중: 비밀번호 해싱 결정 및 회원가입 API 구현

**관련 마일스톤**: M1 (백엔드 기초) → 진행 중

**한 일**
- 비밀번호 해싱 라이브러리 결정 (01 문서 10장 미결정 사항 해소)
- `app/core/security.py` — argon2-cffi 기반 `hash_password` / `verify_password`
- `app/core/db.py` — `async_sessionmaker` 추가 (`expire_on_commit=False`)
- `app/deps.py` — 요청별 DB 세션 의존성 `get_db` (`yield`로 반납 보장)
- `app/schemas/user.py` — `UserCreate` / `UserRead`
  - email 소문자 정규화, 닉네임 앞뒤 공백 제거(`mode="before"`)
  - `UserRead`에 `password_hash`를 넣지 않아 응답 누출을 구조로 차단
- `app/routers/auth.py` — `POST /api/auth/register`
  - 1차 조회로 중복 이메일 409, 2차로 `IntegrityError`를 잡아 같은 409 반환
- Swagger에서 회원가입 흐름 검증 6건
  - 대문자 이메일 · 공백 닉네임 입력 → 201, 소문자 · 공백 제거 저장 확인
  - 동일 이메일 재요청 → 409
  - **대소문자만 바꾼 이메일 → 409** (정규화가 실제로 중복을 막는지 확인)
  - 비밀번호 8자 미만 / 이메일 형식 오류 / 공백만 입력한 닉네임 → 422
- HeidiSQL 검증 — `password_hash`에 원문이 없고 argon2id 형식으로 저장됨, `email` 소문자, `id = 1`, `refresh_tokens` 0행

**결정 기록**
- **비밀번호 해싱은 argon2-cffi (Argon2id)**
  후보는 passlib · bcrypt · argon2-cffi 셋. passlib은 2020년 이후 유지보수가 멈췄고 bcrypt 4.x 이상과 호환이 깨져 제외(FastAPI 공식 튜토리얼이 아직 passlib 기준이라 검색 결과 대부분이 이 방식이다). bcrypt는 72바이트 초과분을 잘라내는데 한글은 글자당 3바이트라 24자면 경계에 닿는다. argon2-cffi는 길이 제한이 없고, 해시 문자열에 계산 파라미터가 포함돼 나중에 강도를 올려도 기존 해시를 그대로 검증할 수 있다(`check_needs_rehash`). 대신 검증 1회에 64MiB · 수십 ms가 들어 테스트가 느려질 수 있으며, 그때는 `argon2.profiles`의 저비용 프로필을 쓴다
- **이메일 중복은 400이 아닌 409**
  요청 자체는 형식이 맞으므로 400(잘못된 요청)이 아니라 현재 상태와의 충돌인 409가 의미에 맞다. v0에서 400을 쓴 것은 DRF 기본 동작을 따랐던 것
- **가입 시 계정 존재 여부 노출(enumeration)을 열어둠**
  "이미 사용 중인 이메일"을 알려주면 제3자가 특정 이메일의 가입 여부를 확인할 수 있다. 막으려면 가입을 항상 성공으로 응답하고 메일로 안내해야 하는데, 이는 SMTP 구성 · 인증 토큰 테이블 · 화면 추가까지 딸려오는 범위 확대라 v1.0에서 제외한다. 대신 **로그인 쪽은 막는다** (다음 세션 구현 예정) — 04 문서 3.1절의 메시지 통일에 더해, 없는 계정에도 더미 해시로 검증을 한 번 돌려 응답 시간을 맞춘다(argon2가 느려 "계정 있음 ≈ 50ms / 없음 ≈ 2ms"로 갈리는 것을 메시지와 무관하게 구분당할 수 있음). 완전 차단은 01 문서 4.4절 F-27로 이관

**막혔던 점 / 트러블슈팅**
- 증상: `verify_password`에 해시 자리로 한글 문자열을 넣자 `False`가 아니라 `UnicodeEncodeError`가 발생
  - 원인: argon2-cffi는 비밀번호를 utf-8로, 해시를 **ascii**로 인코딩한다. argon2가 생성한 해시는 항상 ASCII이기 때문이다. 한글은 인코딩 단계에서 터져 `InvalidHashError` 판정까지 가지도 못함
  - 해결: `except`에 `UnicodeEncodeError`를 추가
  - 교훈: 래퍼 함수가 "맞으면 True, 아니면 False"를 약속했다면 예외가 밖으로 새면 안 된다. 그대로 두면 로그인 라우터에서 401이 아니라 500이 나간다. ASCII 쓰레기값(`"notahash"`)은 정상적으로 `False`가 나와 한글일 때만 드러나는 함정이었다
- 증상: `auth.py`에 `"(" was not closed` 에러. Pylance가 가리킨 줄은 `User(` 괄호가 열린 줄
  - 원인: 실제 원인은 두 줄 아래 `password_hash=...` 끝의 쉼표 누락. 괄호가 안 닫힌 것으로 해석됨
  - 해결: 쉼표 추가
  - 교훈: 괄호 에러는 표시된 위치가 아니라 그 아래에 원인이 있다

**배운 것**
- Pydantic validator의 `mode="before"`는 타입 · 길이 검사보다 먼저 실행된다. 공백만 입력한 닉네임의 422 응답에 `"input": ""`이 찍혀 공백 제거가 길이 검사보다 앞섰음이 확인됐다. 기본값(`after`)이었다면 `"  "`가 `min_length=2`를 통과한 뒤 털려 빈 닉네임이 저장됐을 것이다
- Pydantic은 첫 오류에서 멈추지 않고 모든 검증 오류를 모아 한 번에 반환한다. `detail` 배열의 `loc`에 필드명이 들어 있어 화면에서 해당 입력칸에 연결할 수 있다
- SERIAL 번호는 "어디서 막혔는지"에 따라 소모 여부가 갈린다. 1차 조회에서 409로 막힌 요청은 INSERT를 시도하지 않아 번호를 쓰지 않으므로 `users.id`가 1로 시작했다. 지난 세션 `entries`가 6부터 시작한 것은 INSERT를 실제로 날렸다가 CHECK에 걸린 경우였다
- `created_at`이 `2026-09-19 23:19:00+00`으로 저장됐다. `timestamptz`라 UTC로 보관되며, 한국 시간 표시는 화면에서 변환한다 (03 문서 2.0절)

**다음에 할 일**
- 로그인 — access 토큰(응답 본문) + refresh 쿠키(httpOnly, 프로젝트 접두사), 없는 계정에도 더미 해시 검증
- 토큰 재발급(rotation) → 로그아웃 → `get_current_user` 의존성
- 작업 PC를 노트북 → 집 PC로 이동 (`git pull` 먼저)

---

## 2026-09-19(저녁~밤/집 PC) — M1 진행 중: 모델 6종 정의 및 첫 마이그레이션 적용

**관련 마일스톤**: M1 (백엔드 기초) → 진행 중

**한 일**
- `app/models/base.py` — `DeclarativeBase` 상속 `Base` 선언, 제약조건 작명 규칙(`naming_convention`) 정의
- v1.0 범위 모델 6종 정의 (03 문서 2장 기준)
  - `user.py` — `users`, `refresh_tokens`
  - `game.py` — `games`, `genres`, `game_genres`
  - `entry.py` — `entries`
- `app/models/__init__.py` — 전체 모델을 한자리에 import (Alembic이 테이블을 인식하는 통로)
- `alembic/env.py` — `target_metadata`에 `Base.metadata` 연결
- 첫 마이그레이션 생성(`0a6ba7b72cfb`) → `upgrade head --sql`로 DDL 확인 → 적용
- HeidiSQL에서 제약 동작 검증 — 위반값을 실제로 INSERT/DELETE해 11건 확인
  - CHECK 5종(status · source · 구매가 · 플레이타임 · 평점) 차단
  - NULL은 CHECK를 통과하는 것 확인 (구매가 없는 Steam 게임 대비)
  - UNIQUE 2종(`(user_id, game_id)` · `email`), `ck_users_password_needs_email` 차단
  - FK 삭제 규칙 — 참조 중인 게임 삭제 거부(RESTRICT), 사용자 삭제 시 `entries` 연쇄 삭제(CASCADE)
  - 검증 데이터 전부 삭제해 마이그레이션 직후 상태로 복원

**결정 기록**
- **`Base`를 `core/db.py`가 아닌 `models/base.py`에 둠**
  인터넷 예제 다수가 엔진과 `Base`를 한 파일에 두지만, 02 문서 6장에서 `core/`는 "설정 · DB 연결 · 보안", `models/`는 "테이블 정의"로 나눠 두었음. `Base`는 연결이 아니라 테이블 정의의 공통 조상이므로 `models/` 소속. 의존 방향이 `models/` → `core/` 한쪽으로만 흘러 순환 import를 원천 차단하는 효과도 있음
- **제약조건 작명 규칙(`naming_convention`)을 `Base`에 미리 부여**
  규칙이 없으면 PostgreSQL이 `entries_check` 같은 이름을 자동 부여해, 나중에 특정 제약만 삭제 · 수정할 때 대상을 지목할 수 없음. 실제로 검증 단계에서 에러 메시지에 `ck_entries_rating_range`처럼 이름이 찍혀 5개 CHECK 중 무엇이 걸렸는지 즉시 판별됨
- **`game_genres`를 ORM 클래스가 아닌 Core `Table` 객체로 정의**
  컬럼이 `(game_id, genre_id)` 둘뿐이고 추가할 정보가 없음(03 문서 2.5절). 클래스로 만들면 연결 하나마다 빈 객체를 생성하게 됨. 대신 나중에 연결 자체에 속성이 필요해지면 클래스로 전환하는 마이그레이션이 필요하다는 점을 감수함 — M8 작업 목록에 장르 동기화가 없어 당분간 발생하지 않을 것으로 판단
- **`entries.source`를 M8이 아닌 지금 생성**
  Steam 동기화(M8)에서 쓰는 컬럼이지만, NOT NULL 기본값 `MANUAL`이라 지금 넣어도 v1.0 동작에 영향이 없음. 나중에 NOT NULL 컬럼을 추가하려면 기존 행 처리를 고민해야 하므로 처음부터 포함

**막혔던 점 / 트러블슈팅**
- 증상: `alembic upgrade head`가 성공 로그(`Running upgrade -> 0a6ba7b72cfb`)를 남겼는데 HeidiSQL에 테이블이 보이지 않음. 새로고침을 10회 이상 반복함
  - 원인: HeidiSQL 세션의 "데이터베이스" 칸이 비어 있어, 같은 컨테이너(5434)의 **기본 DB인 `postgres`** 에 접속돼 있었음. 트리 상단에는 세션 이름인 `playledger`가 표시돼 접속 대상이 맞는 것처럼 보였고, 접속 · 쿼리 실행도 전부 정상이라 알아채기 어려웠음
  - 해결: 세션 관리자의 데이터베이스 칸에 `playledger`를 명시하고 재접속. `SELECT current_database(), current_user, current_schema()`로 실제 접속 대상을 확인한 뒤 테이블 7개 확인
  - 교훈: 접속 정보는 호스트 · 포트 · 사용자 · **DB 이름** 네 가지이고, 하나만 어긋나도 엉뚱한 곳에 정상적으로 접속된다. M0의 `paths`/`path` 오타와 같은 유형 — 값을 **안 주면** 에러가 아니라 기본값으로 대체돼 조용히 넘어간다. "분명 넣었는데 없다"가 나오면 트리 새로고침 대신 `SELECT current_database(), current_user, current_schema()` + `SHOW data_directory` 두 줄로 "나는 지금 어디에 있는가"부터 확인할 것
- 증상: 위 문제의 원인을 포트 불일치(5432 Windows 설치본 vs 5434 컨테이너)로 먼저 의심함
  - 원인: 포트만 확인하고 결론을 내림. `SHOW data_directory`가 컨테이너 경로를 반환해 가설이 반증됐는데도 재확인 범위를 넓히지 않았음
  - 해결: `pg_tables` · `pg_class`를 직접 조회해 "테이블이 이 DB에 아예 없다"를 확정한 뒤, `current_database()`로 접속 대상을 특정
  - 교훈: M0의 "포트 충돌로 오인" 사례와 동일한 실수를 반복했다. 가설을 세우는 것은 괜찮지만, 반증 증거(`SHOW data_directory` 결과)가 나왔을 때 가설을 버리고 확인 범위를 넓혀야 한다

**배운 것**
- `--sql` 출력 전체가 `BEGIN; ... COMMIT;`으로 감싸여 있음. PostgreSQL은 DDL도 트랜잭션으로 묶이므로 마이그레이션이 중간에 실패하면 앞서 만든 테이블까지 전부 롤백된다(MariaDB는 DDL이 트랜잭션 대상이 아니라 반쯤 생성된 상태가 남음). 적용 로그의 `Will assume transactional DDL`이 이 의미
- CHECK 제약은 값이 NULL이면 통과한다. SQL에서 NULL과의 비교 결과는 참도 거짓도 아닌 UNKNOWN이고, CHECK는 거짓일 때만 차단하기 때문. `purchase_price >= 0`이 걸려 있어도 구매가 미상(NULL)인 Steam 게임은 정상적으로 등록된다
- SERIAL이 뽑은 번호는 INSERT가 실패해도 반환되지 않는다. 검증 중 차단된 INSERT 5건 때문에 `entries.id`가 1~5를 건너뛰고 6부터 시작함. id는 순서나 개수가 아니라 식별자일 뿐
- `DELETE FROM users` 결과의 "영향 받은 행: 1"에 CASCADE로 연쇄 삭제된 `entries` 행은 포함되지 않는다. 편리한 만큼 영향 범위가 응답에 드러나지 않는다는 점을 유의

**다음에 할 일**
- 비밀번호 해싱 라이브러리 결정 (01 문서 10장) 후 회원가입 API
- 로그인(access 토큰 + refresh 쿠키) → 토큰 재발급(rotation) → 로그아웃 → `get_current_user` 의존성
- 초기 장르 데이터 시드는 게임 CRUD 착수 전까지 진행

---

## 2026-09-19(오전~오후/집 PC) — M0 완료: FastAPI · Vue 구성 및 화면 → 서버 → DB 연결 확인

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
  8000은 다른 개인 프로젝트(콕)의 FastAPI와 겹칠 수 있음. DB 5434와 같은 원리로 프로젝트별 전용 번호를 배정해 두 프로젝트를 동시에 켜도 충돌하지 않게 함. 05 문서 완료 기준의 포트 표기도 함께 수정
- **커밋 단위를 파일 단위 → 작업 파트 단위로 조정**
  M0 초반에는 파일 한두 개마다 커밋해 커밋 메시지 작성 시간이 코드 작성 시간을 넘어섰음. 기준을 지침의 *"이것만 따로 되돌리고 싶을 수 있는가?"* 로 되돌려 적용 — venv · FastAPI · 설정 · 엔진 · Alembic은 하나가 빠지면 나머지가 무의미하므로 한 덩어리. M1부터는 "완결된 동작"(회원가입, 로그인) 단위로 함
- **shadcn-vue는 init만 하고 컴포넌트는 받지 않음**
  shadcn-vue는 라이브러리 설치가 아니라 컴포넌트 소스를 프로젝트에 복사해 넣는 방식이라, 쓰지 않을 컴포넌트를 미리 받으면 그대로 죽은 코드가 됨. 필요한 것만 M2에서 받는다
- **빈 폴더 · 미사용 규칙을 선제적으로 만들지 않음**
  02 문서 구조도에 있는 `core/`, `models/`, `schemas/` 등을 미리 만들지 않고 쓸 내용이 생길 때 생성. `.gitignore`에서도 사용하지 않는 규칙(`dist-ssr`, `.DS_Store`, macOS · Visual Studio 관련)을 제외

**막혔던 점 / 트러블슈팅**
- 증상: `uvicorn app.main:app --reload` 실행 시 `Error loading ASGI app. Could not import module "app.main"`. 포트 충돌로 의심해 `--port 8001`로 바꿨더니 동작해서 포트 문제로 오인
  - 원인: 실제로는 `main.py`가 아직 디스크에 저장되지 않은 상태였음. 로그를 보면 `Uvicorn running on http://127.0.0.1:8000`까지는 정상이었으므로 포트는 처음부터 문제가 아니었음
  - 해결: 파일 저장 후 정상 기동
  - 교훈: 에러 메시지가 말하는 것을 그대로 읽을 것. import 실패는 `Could not import module`, 포트 충돌은 `address already in use`로 각각 명시된다. 짐작으로 조건을 바꾸면 우연히 해결돼도 원인을 모른 채 넘어간다
- 증상: 설정 로딩 검증 중 `print(settings.database_url)`로 DB 비밀번호가 터미널에 원문 출력됨
  - 원인: 검증 목적에 필요한 것은 "값이 로딩됐는가"인데 값 전체를 출력하도록 명령을 구성함
  - 해결: 볼륨이 비어 있는 시점(테이블 0개)이라 손실 없이 비밀번호 교체 — 루트 `.env`와 `server/.env`를 함께 수정하고 `docker compose down -v` 후 재생성. 이후 검증은 `settings.database_url.split('@')[-1]`로 접속 주소만 출력
  - 교훈: 비밀값은 확인 과정에서도 원문을 노출하지 않는다. 02 문서 7장에 적어둔 "비밀번호를 바꿀 땐 두 파일을 함께 고친다" 규칙이 실제로 처음 적용된 사례이기도 하다
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
- shadcn-vue init이 Inter 폰트를 구글 서버에서 받아오는 방식으로 `style.css`에 추가함. M5 배포 시 프로젝트 내장 여부를 검토 (05 M5에 항목 추가)

**다음에 할 일**
- M0 PR 생성 후 `main`에 병합 (M0는 CI 없음), `m1-backend` 브랜치 생성
- M1 착수: v1.0 범위 모델 정의(`users`, `refresh_tokens`, `games`, `genres`, `game_genres`, `entries`) → 첫 마이그레이션을 `--sql`로 확인

---

## 2026-09-18(저녁~밤/집 PC) — M0 진행 중: 공통 설정 및 PostgreSQL 컨테이너 구성

**관련 마일스톤**: M0 (환경 구성) → 진행 중

**한 일**
- `m0-setup` 브랜치 생성 (브랜치 전략 전환 첫 적용)
- `.gitignore`를 새 스택 기준으로 재작성 — 비밀값 · Python · Node · 로그 · OS 구역으로 분리
- `.gitattributes` 추가 — `* text=auto eol=lf`로 줄바꿈 규칙을 저장소 차원에서 고정
- `docker-compose.yml` 작성 — `postgres:18`, 이름 붙은 볼륨, healthcheck, `127.0.0.1` 바인딩
- 루트 `.env` / `.env.example` 분리 (Compose용 DB 계정)
- HeidiSQL로 컨테이너 접속 확인, `SHOW data_directory`로 "컨테이너 DB에 붙었다"까지 검증
- 02 문서 v1.1 개정 — 루트 `.env` 추가, 구조도에 `.gitattributes` 반영, Redis 도입 시점 표기 수정

**결정 기록**
- **Compose용 DB 계정을 루트 `.env`로 분리**
  Docker Compose는 compose 파일과 같은 폴더의 `.env`를 자동으로 읽는다. `server/.env`를 `env_file`로 통째로 넘기면 DB 컨테이너가 쓰지도 않는 JWT 서명 키 · Steam API 키까지 받게 되므로, DB 계정만 루트 `.env`로 분리. 대신 같은 비밀번호가 두 파일에 존재하므로 "바꿀 땐 함께 고친다"를 02 문서 7장에 규칙으로 명시
- **호스트 포트를 5434로 고정**
  5432는 Windows에 설치된 PostgreSQL 18 서비스, 5433은 다른 개인 프로젝트(콕) 컨테이너가 사용 중. 포트를 비켜 앉는 대신 프로젝트별 전용 번호를 배정해, 학교 PC를 포함한 어느 환경에서도 같은 설정이 동작하도록 함
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

## 2026-09-18(오후~저녁/집 PC) — M0 재착수: 스택 전환 결정 및 설계 문서 전면 개정

**관련 마일스톤**: M0 (환경 구성) → 진행 중

**한 일**
- 기존 구현(M1 완료, M2 네비게이션 골격)을 `v0-rn-django` 태그로 보존
- 구 스택 코드(`app/`, `server/`) 제거 및 빌드 찌꺼기 정리
- 설계 문서 전면 개정 (01 ~ 05, README)
  - `ERD.md` → `03_erd.md`로 파일명 변경 (`git mv`로 이력 유지)
  - 구조도 · 인증 · 동기화 · 화면 흐름을 mermaid로 전환
  - 01에 유즈케이스, 04에 화면 흐름 · 상태 전환 · 시퀀스 다이어그램 추가
- 마일스톤을 M0 ~ M11, 버전별(v1.0 ~ v2.1)로 재구성

**결정 기록**
- **스택 전환 (RN + Django + MariaDB → Vue 3 + FastAPI + PostgreSQL)**
  취업으로 프로젝트 목적이 포트폴리오 → 자기계발 · 취미로 바뀜. 함께 준비하던 별도 프로젝트(단축 URL 서비스 '콕')는 기술 스택을 먼저 정하고 주제를 끼워 맞춘 탓에 재미가 없어 접고, 그 스택을 문제의식이 분명한 PlayLedger에 적용. 전환 시점의 구현량이 M1 + 네비게이션 골격이라 버리는 비용이 작았음. 기술별 근거는 `02_architecture.md` 3장
- **모바일 앱 → 반응형 웹**
  v0의 "PC 앞이 아닐 때" 시나리오를 다시 따져보니, 기록과 분석이 실제로 일어나는 순간은 Steam을 켜둔 PC 앞이 더 많음. 모바일은 반응형으로 대응 (`01` 3.2절에서 "웹 제외"를 반전)
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
- 증상: 문서 검수 중 문서끼리 서로 다른 말을 하는 곳이 여러 번 발견됨 (R-02 "자동 폴링 안 함" vs F-19 자동 동기화, 02 문서 안에서 Redis 도입 시점 M8 vs M9, v0부터 있던 F-02 플랫폼 항목 vs ERD)
  - 원인: 문서 여러 개를 한 번에 개정하면서, 같은 사실을 다른 문서에서도 말하고 있는지 대조하지 않음
  - 해결: 커밋 전 검수 단계에서 하나씩 정정
  - 교훈: 설정을 바꾸면 그 값을 참조하는 곳을 검색하듯, 문서도 바꾼 내용의 핵심어(예: "자동 동기화", "Redis")로 `docs/` 전체를 검색해 어긋난 곳이 없는지 확인할 것
- 증상: 02 문서의 Discord 로그인 시퀀스와 비밀번호 해시 비교 위치가 실제로는 틀린 흐름이었음 (mermaid는 문법 오류 없이 그림이 잘 그려짐)
  - 원인: 콜백은 fetch 응답이 아니라 브라우저 페이지 이동이라 access 토큰을 응답 본문으로 받을 수 없음. 해시 비교는 DB가 아니라 서버가 함
  - 해결: 콜백에서는 refresh 쿠키만 심고 프론트가 재발급 API로 access 토큰을 받는 흐름으로 수정
  - 교훈: M1 때 "서버가 에러 없이 뜬다고 코드가 의도대로 동작하는 건 아니다"와 같다. **다이어그램이 그려진다고 흐름이 맞는 건 아니다.** 그림도 코드처럼 흐름을 따라가며 검수해야 한다
- 증상: 03 문서 변경 이력의 v0.2 줄이 `(기존 내용 유지)`라는 자리표시로 덮여 커밋 직전까지 감
  - 원인: 안내받은 블록 안의 자리표시를 그대로 옮겨 적음
  - 해결: 검수 단계에서 발견해 원문 복구
  - 교훈: 문서를 크게 고친 뒤엔 커밋 전에 `git diff`로 **삭제된 줄(`-`)** 을 한 번 훑어볼 것. 의도하지 않은 삭제는 추가된 줄보다 삭제된 줄에서 잘 보인다
- 증상: 03 문서만 줄바꿈 형식이 CRLF(나머지는 LF)
  - 원인: VS Code에서 새로 만든 파일이 Windows 기본값을 따름
  - 해결: 보류 (Git이 커밋 시 변환). M0에서 `.gitattributes`로 근본 해결 예정

**다음에 할 일**
- M0 착수: `.gitignore` 재작성 → `.gitattributes` → Docker Compose(PostgreSQL) → FastAPI 헬스체크 → Vite 프로젝트 → 프록시 연결
- Project Instructions의 구 스택 표현 갱신 (파일명, 폴더 구조, 스택명)

---

## 2026-08-17 — M2 착수: React Navigation 세팅 및 네비게이션 골격 구현

**관련 마일스톤**: M2 (앱 연동) → 진행 중

**한 일**
- React Navigation 패키지 설치 (`@react-navigation/native`, `bottom-tabs`, `native-stack`, `react-native-screens`, `react-native-safe-area-context`)
- `src/navigation/RootNavigator.tsx` — 로그인 여부(현재는 임시 state)에 따라 LoginScreen/MainTabs 분기
- `src/navigation/MainTabs.tsx` — 하단 탭 3개(라이브러리/통계/설정) 등록
- `src/navigation/LibraryStack.tsx` — 라이브러리 탭 내부 스택 뼈대 (S-03/S-04는 추후 추가 예정)
- `src/screens/` — Login/Library/Stats/Settings 4종 placeholder 화면 작성
- `App.tsx`를 RN 기본 템플릿에서 RootNavigator 호출로 교체
- 에뮬레이터(Pixel 8, API 37.1) 처음 생성 및 실행 확인
- 탭 3개 전환 및 각 화면 렌더링 실기기/에뮬레이터에서 확인

**막혔던 점 / 트러블슈팅**
- 증상: `run-android` 실행 시 에뮬레이터에서 빨간 에러 화면(`Unable to load script`)
  - 원인: 실기기와 에뮬레이터를 동시에 연결한 상태로 `run-android`를 실행해 Metro 연결이 두 기기로 분산되며 꼬임
  - 해결: 에뮬레이터 완전 종료 → Metro 재시작(`--reset-cache`) → 재연결로 해결
  - 교훈: 에뮬레이터로 작업할 땐 실기기 USB를 뽑아두는 편이 연결 문제를 줄인다
- 증상: `npm install @react-native-screens ...` 실행 시 `EINVALIDTAGNAME` 에러
  - 원인: 스코프 없는 패키지(`react-native-screens`)에 실수로 `@`를 붙여 스코프 패키지로 오인시킴
  - 해결: `@` 제거 후 재실행
  - 교훈: `@단체명/패키지명` 형태(스코프 패키지)와 `패키지명`만 있는 형태를 헷갈리지 않도록 설치 전 npm 페이지에서 정확한 이름 확인

**다음에 할 일**
- API 호출 모듈 작성 (`api/`) — 이 작업과 함께 `03_api_spec.md` 작성 착수
- S-01 로그인 화면 실제 폼 구현, 토큰 저장(AsyncStorage) 연결

---

## 2026-08-17 — M1 완료: 게임 CRUD (Serializer·View·URL) 완료, 계정 격리 검증까지 완료

**관련 마일스톤**: M1 (백엔드 기초) → 완료

**한 일**
- `library/utils.py` 작성 — `normalize_title()`, 제목 정규화 함수 (공백/대소문자/특수문자 제거)
- `library/serializers.py` 작성 — `GenreSerializer`, `GameSerializer`, `EntrySerializer`
  - `_resolve_game()`으로 ERD 2.2절 중복 판별 순서(steam_appid → title_norm) 구현
  - 같은 사용자가 같은 게임 중복 등록 시 400 응답으로 차단 (DB IntegrityError로 500 나가는 것 방지)
- `library/views.py` 작성 — `EntryViewSet`, `get_queryset()`으로 로그인한 사용자 소유 데이터만 필터링
- `library/urls.py` 작성 — `DefaultRouter`로 `/entries/` 라우팅, `config/urls.py`에 연결
- `library/admin.py`에 `GameAdmin` 추가 — `title_norm` readonly 처리 + `save_model`에서 자동 계산
- 브라우저(admin 계정) + PowerShell(신규 tester 계정)로 전체 흐름 실증 테스트
  - 비로그인 `/entries/` → 401 확인
  - 로그인 후 등록(201) → 재등록 시 중복 차단(400) 확인
  - `tester` 계정으로 조회 시 `admin`이 등록한 기록이 안 보임(빈 배열) 확인 — **M1 완료 기준 충족**

**막혔던 점 / 트러블슈팅**
- 증상: `serializers.py` 작성 중 `validate_rating` 등 메서드 6개가 `class Meta:` 블록 다음부터 들여쓰기 없이 이어짐. `runserver`는 에러 없이 뜨고 `_resolve_game`이 "사용되지 않는 것 같다"는 감이 들어서 발견
  - 원인: 들여쓰기가 0칸이라 해당 메서드들이 `EntrySerializer` 클래스 밖으로 빠져나가 독립 함수가 됨. `self`가 진짜 인스턴스를 가리키지 않게 되고, DRF가 이 메서드들을 전혀 호출하지 않음. 파이썬 문법상으로는 완전히 유효한 코드라 서버 기동은 정상적으로 됨
  - 해결: `# ── 개별 검증 필드 ──` 줄부터 파일 끝까지 전체를 4칸 들여써서 클래스 본문 안으로 이동
  - 교훈: 서버가 에러 없이 뜬다고 코드가 의도대로 동작하는 건 아니다. Python은 들여쓰기가 유일한 문법 신호라서, 메서드가 클래스 밖으로 새어나가도 아무 경고가 없다. 클래스 안에 있어야 할 코드는 매번 들여쓰기 레벨을 눈으로 직접 확인해야 한다
- 증상: API로 "발더스 게이트 3"을 등록했더니 `games` 테이블에 같은 제목의 게임이 2행 생성됨 (`_resolve_game`이 기존 게임을 못 찾음)
  - 원인: 이전에 admin 화면에서 "발더스 게이트 3"을 손으로 먼저 등록했었는데, 그때 `title_norm` 칸이 자유 입력 텍스트필드로 노출돼 있어서 실제 `normalize_title()` 결과(`발더스게이트3`)와 무관한 값(`balder'sgate3`, 어퍼스트로피까지 남아있어 정규화 함수를 거치지 않은 게 확실함)이 저장됨. API가 나중에 title_norm으로 비교했을 때 일치하는 게 없어 새 게임으로 판단
  - 해결: `GameAdmin`에 `title_norm`을 `readonly_fields`로 지정하고, `save_model()`에서 `title` 기준으로 서버가 강제로 재계산하도록 변경. 기존 중복 행은 admin에서 수동 삭제
  - 교훈: "기계가 계산해야 할 값"을 사람이 만질 수 있는 화면에 그대로 노출하면, 그 값을 신뢰하는 다른 로직(`_resolve_game`)이 전부 무력화된다. admin 화면도 API와 동일한 신뢰 경계 안에 있다고 가정하면 안 되고, 자동 계산 필드는 진입 경로에 상관없이 항상 서버가 강제해야 한다

**다음에 할 일**
- M1 완료 기준 전부 충족 확인됨 → `05_milestones.md` M1 섹션 완료 처리
- `03_api_spec.md` 작성 착수 (M1 완료 후 작성 규칙에 따라)
- M2(RN 화면 연동) 착수 전, F-02 장르 입력 미구현 건은 `05_milestones.md`에 별도 작업 항목으로 남겨둠 — M2 앱 화면 설계와 함께 진행 예정

---

## 2026-08-17 — M1 진행 중: 인증 파트 (DRF 설정·회원가입·로그인) 완료

**관련 마일스톤**: M1 (백엔드 기초) → 진행 중

**한 일**
- INSTALLED_APPS에 rest_framework, rest_framework.authtoken 추가
- REST_FRAMEWORK 전역 설정 (TokenAuthentication + SessionAuthentication, IsAuthenticated 기본값)
- authtoken 마이그레이션 실행, HeidiSQL/sqlmigrate로 authtoken_token 테이블 구조 확인
- RegisterSerializer/RegisterView 작성, /auth/register/ 연결 및 실제 계정 생성 확인
- 로그인 라우팅(obtain_auth_token) 연결, 토큰 발급 및 오답 비밀번호 거부(400) 확인

**막혔던 점 / 트러블슈팅**
- 증상: REST_FRAMEWORK 설정을 넣었는데도 admin 화면이 평소처럼 잘 됨
  - 원인: `DEFAULT_AUTHENTICATION_CLASSES`를 `DEFAULT_AUTHENICATION_CLASSES`로 오타
    (`rest_framework.authentication`도 `authenication`으로 오타). Django/DRF가 
    이런 키 오타를 에러 없이 조용히 무시하고 기본값으로 폴백함
  - 해결: 오타 수정
  - 교훈: 설정 딕셔너리 키 오타는 서버가 정상 기동돼도 잡히지 않는다. 
    admin이 잘 되는 건 세션 쿠키 때문이지 내 설정이 적용된 증거가 아님 — 
    실제 토큰 인증 흐름을 태워봐야 진짜 검증이 됨
- 증상: PowerShell에서 curl.exe로 로그인 POST 시 "JSON parse error - 
  Expecting property name..." 반복 발생 (작은따옴표로 감싸도 동일)
  - 원인: curl.exe는 네이티브 실행파일이라 PowerShell이 인자를 넘길 때 
    Windows 커맨드라인 재조합 규칙을 한 번 더 거침 → JSON 내 큰따옴표가 
    깨져서 전달됨
  - 해결: PowerShell 네이티브 명령어(`Invoke-RestMethod` + `ConvertTo-Json`)로 전환
  - 교훈: Windows PowerShell 환경에서는 curl.exe보다 Invoke-RestMethod가 
    안정적. 이후 API 테스트는 이 방식을 기본으로 사용

**다음에 할 일**
- M1 게임 CRUD: Serializer 작성 → 목록 조회(본인 데이터만) → 등록(중복 판별) → 
  단건 조회/수정/삭제 → 쿼리셋 필터로 사용자 격리 이중 적용
- CRUD 완성 후 계정 2개로 교차 확인 (M1 완료 기준 검증)

---

## 2026-08-14 — M1 진행 중: accounts/library 모델 정의 및 마이그레이션까지 완료

**관련 마일스톤**: M1 (백엔드 기초) → 진행 중

**한 일**
- `accounts`, `library` 앱 생성
- 커스텀 `User` 모델 작성 (`AbstractUser` 확장, `steam_id` 추가) 및 `AUTH_USER_MODEL` 지정
- 커스텀 User 모델은 첫 migrate 이전에 결정해야 한다는 것을 확인 → 기존 M0 DB를 DROP 후 재생성하고 진행
- `library` 모델 4종(`Game`/`Genre`/`GameGenre`/`Entry`) 작성, ERD 그대로 반영
  - `Entry`에 복합 UNIQUE(`uq_user_game`), 인덱스(`idx_user_status`) 적용
- `settings.py` 정리: `EMAIL_BACKEND` 오타 수정, `TIME_ZONE`을 `Asia/Seoul`로 변경
- 관리자 계정 생성 및 `/admin/`에서 장르 3개, 게임 1개 입력 테스트 → 정상 동작 확인

**막혔던 점 / 트러블슈팅**
- 증상: `python managy.py startapp` 오타로 실행 실패
   - 원인: 단순 오타 (`manage.py` → `managy.py`)
   - 해결: 재입력
   - 교훈: 명령어 오타는 파일 탐색기로 실제 파일 존재 여부를 먼저 확인하면 빠르게 판별 가능
- 증상: VS Code Problems 탭에 `django`/`dotenv` import 미해결 경고 4건 지속
   - 원인: Pylance가 venv 인터프리터를 제대로 인식하지 못함 (인터프리터 재선택 시도 중 루트에 불필요한 venv 생성 시도 발생, 취소함)
   - 해결: `pip show django`/`pip show python-dotenv`로 실제 venv(`server/venv`)에 정상 설치됨을 확인 → 실행에는 영향 없는 편집기 표시 문제로 판단하고 보류
   - 교훈: Problems 탭 경고가 실제 실행 가능 여부와 항상 일치하는 건 아님. `pip show`로 실제 설치 위치를 확인하는 게 더 확실한 판단 근거
- 증상: `createsuperuser`에서 약한 비밀번호 경고를 무시하고 생성 → 이후 `/admin/` 로그인 반복 실패
   - 원인: 취약한 비밀번호 및 브라우저 자동완성이 다른 프로젝트의 저장된 비밀번호를 잘못 채워 넣었을 가능성
   - 해결: `python manage.py changepassword admin`으로 비밀번호 재설정 후 정상 로그인
   - 교훈: 비밀번호 검증 경고는 로컬 개발 환경이라도 가급적 무시하지 않는 편이 나음

**다음에 할 일**
- M1 인증 파트: DRF `TokenAuthentication` 설정, 회원가입 API, 로그인/토큰 발급 API, 권한 클래스(비로그인 접근 차단) 적용

---

## 2026-08-14 — M0 완료: Django-MariaDB-RN 환경 구성
 
**관련 마일스톤**: M0 (환경 구성) → 완료
 
**한 일**
- Git 저장소 초기화, `.gitignore` 배치 (Django `.env`/`venv`, RN `node_modules`, DB 파일 제외 확인)
- Python venv 생성, Django + DRF 설치, `server/config` 프로젝트 생성
- `runserver` 로켓 화면으로 Django 정상 실행 확인
- MariaDB에 `playledger` DB 생성 (`utf8mb4`/`utf8mb4_unicode_ci`)
- `mysqlclient`, `python-dotenv` 설치, `.env`/`.env.example` 분리
- `settings.py`를 SQLite → MariaDB로 전환 (`DATABASES`, `SECRET_KEY`를 환경변수화)
- `migrate` 실행, HeidiSQL에서 `playledger` DB에 테이블 11개 생성 확인
- React Native CLI로 `app/` 프로젝트 생성 (RN 0.87.0)
  - 생성 시 자동으로 만들어진 `app/.git` 별도 저장소를 제거해 루트 저장소로 통합
  - `ANDROID_HOME` 환경변수 및 `Path`(`platform-tools`) 등록
  - 실기기(USB) `adb` 인증 → `run-android` 빌드 성공 → Metro 번들러 연결 → 앱 정상 실행 확인

**막혔던 점 / 트러블슈팅**
- 증상: `CREATE DATABASE` 시 `Unknown collation: 'utfmb4_unicode_ci'` 에러
   - 원인: 콜레이션 이름 오타 (`utfmb4` → `utf8mb4` 누락)
   - 해결: `utf8mb4_unicode_ci`로 정정 후 재실행
   - 교훈: `utf8mb4` 관련 옵션은 철자 하나만 틀려도 조용히 실패하지 않고 바로 에러로 잡히니, 에러 메시지를 그대로 믿고 다시 치면 됨
- 증상: `adb devices`에 기기가 `unauthorized`로만 표시됨
   - 원인: 폰에서 "USB 디버깅 허용" 팝업을 아직 승인하지 않음
   - 해결: 폰 화면 잠금 해제 후 팝업에서 "이 컴퓨터에서 항상 허용" 체크 후 허용
   - 교훈: PC에서의 인식(daemon 연결)과 폰에서의 인증(authorized)은 별개 단계. `unauthorized`가 뜨면 폰 쪽 조작이 필요하다는 신호
- 증상: `run-android`는 `BUILD SUCCESSFUL`인데 폰에 빨간 에러 화면(`Unable to load script`)
   - 원인: 네이티브 빌드(APK 설치)와 JS 번들 서버(Metro)는 별개 프로세스인데, Metro가 자동으로 안 켜짐
   - 해결: 별도 터미널에서 `npx react-native start`로 Metro 수동 실행 후 앱 재시작
   - 교훈: RN은 "네이티브 껍데기 설치"와 "JS 코드 제공"이 분리된 구조. 둘 다 확인해야 함. 앞으로는 항상 Metro(터미널 1)를 먼저 켜두고 `run-android`(터미널 2)를 실행하는 순서로 진행
- 증상: RN 프로젝트 생성 로그에 `Initializing Git repository`가 찍힘
   - 원인: RN CLI가 `app/` 폴더 안에 독자적인 `.git`을 새로 만듦 (루트 저장소와 중첩)
   - 해결: `app/.git` 폴더 삭제 후 `git status`로 루트 저장소에 정상 편입됐는지 확인
   - 교훈: 하위 폴더에 프로젝트를 생성하는 CLI 도구는 자체적으로 Git 저장소를 만드는 경우가 있으니, 생성 직후 반드시 `.git` 중첩 여부 확인할 것

**결정 기록**
- RN 환경을 **Expo가 아닌 CLI로 확정**. 애초 리스크 대응책(`05_milestones.md` M0 리스크)은 "환경 구성 실패 시 Expo로 우회"였으나, 실제로는 안드로이드 스튜디오가 이미 설치돼 있고 USB 실기기 연결도 준비된 상태라 CLI 진입 장벽이 사실상 없었음. 학습 목적(네이티브 빌드 과정을 직접 보는 것)에도 CLI가 더 부합해 계획대로 진행

**다음에 할 일**
- M1 착수: `accounts`/`library` Django 앱 생성, ERD 기준 모델 정의(`Game`/`Genre`/`GameGenre`/`Entry`), 마이그레이션

---

## 2026-08-13 — 프로젝트 기획 및 문서 작성

**관련 마일스톤**: 기획 단계 → M0 착수 전

**한 일**
- 프로젝트 주제 선정 (게임 백로그 관리)
- 기술 스택 결정: React Native + Django + MariaDB
- 기획 문서 작성
  - `01_requirements.md` — 기능 범위, 계산식, 마일스톤 개요
  - `02_architecture.md` — 전체 구조, 기술 선택 근거, 인증 흐름
  - `04_ui_design.md` — 화면 6종, 네비게이션, 상태 표시 규칙
  - `05_milestones.md` — 단계별 완료 기준, 리스크
  - `ERD.md` — 테이블 5종, 1:N / N:M 관계 설계
- `.gitignore` 작성 (Django `.env` / RN `node_modules` 제외 확인)

**설계 판단 기록**
- `games`와 `entries`를 분리 — 게임 정보가 사용자 수만큼 중복되는 것을 막기 위함
- 장르는 `game_genres` 연결 테이블로 N:M 처리 — 문자열 이어붙이기로는 장르별 통계 불가
- `entries.source` 컬럼 추가 — M5 Steam 동기화 시 수동 입력 데이터를 보호하는 장치
- `03_api_spec.md`는 M1 이후로 미룸 — DRF의 기본 URL 구조를 확인한 뒤 작성하는 편이 정확함

**다음에 할 일**
- M0 착수: Django 프로젝트 생성, MariaDB 연결, RN 프로젝트 생성

---
