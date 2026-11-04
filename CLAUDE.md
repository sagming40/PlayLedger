# CLAUDE.md

이 저장소에서 일하는 Claude가 지키는 공통 규칙이다.
세션끼리는 기억을 공유하지 않고, 기기도 3대(데스크톱 B 회사 · 데스크톱 A 집 · 노트북, 자주 쓰는 순)라서 **저장소가 공용 노트**다. 이 파일과 `docs/`가 기억 역할을 한다.

PlayLedger: 사놓고 안 한 게임을 구매일 · 구매가 · 플레이타임으로 기록하고, 방치일수 · 시간당 비용 · 완주율 같은 숫자로 보여 주는 웹 서비스. 1인 학습 프로젝트다.

## 문서 지도 (질문 하나 = 문서 하나)
| 질문 | 문서 |
|---|---|
| 지금 어디까지 왔고 바로 다음에 뭘 해? | [`docs/DEVLOG.md`](docs/DEVLOG.md) "현재 상태" |
| 겪은 문제와 해결은? | [`docs/DEVLOG.md`](docs/DEVLOG.md) 세션 기록 (최신이 위), 끝난 단계는 [`docs/archive/`](docs/archive/README.md) |
| 왜 이렇게 정했어? | [`docs/decisions/`](docs/decisions/README.md), 작은 판단은 DEVLOG `[설계]` · archive의 "결정 기록" |
| 무엇을 어떤 순서로 만들어? 어디까지 왔어? 완료 기준은? | [`docs/PLAN.md`](docs/PLAN.md) |
| 기능 범위는? 하지 않을 것은? | [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) (범위는 3장, 나중 아이디어는 4.4절) |
| 레이어 · 디렉터리 구조, 인증 흐름은? | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| 클라이언트가 지킬 인증 계약 · 에러 응답 규칙은? | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) 3장 (엔드포인트 목록은 Swagger `/docs`) |
| DB는 어떻게 생겼고 왜? | [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md) (컬럼은 `server/app/models/` · `server/alembic/versions/`) |
| 화면은 어떻게 생겼고 왜? 색 · 테마는? | [`docs/DESIGN.md`](docs/DESIGN.md) (색 · 테마는 4.4절), 그림은 [`docs/mockups/`](docs/mockups/README.md) |
| 이게 뭐고 어떻게 실행해? | [`README.md`](README.md) |
| 작업할 때 항상 지킬 규칙은? | 이 파일 |

- 문서의 기본 틀은 전역 설정의 "문서 체계" 절이다. 코드가 담지 못하는 것만 적고, 코드에서 알 수 있는 것은 원본을 가리킨다
- **전역 문서 체계와 다르게**: `docs/mockups/`의 파일 이름은 `화면.기기.html`이 아니라 `화면.dc.html`로 둔다. 디자인 캔버스 원본의 사본이라 이름을 바꾸면 링크 · `support.js` · `canvas.json`을 같이 고쳐야 하고 캔버스와 어긋날 수 있다 ([decisions/0001](docs/decisions/0001-docs-refactor.md))
- 같은 내용을 두 곳에 쓰지 않는다. 다른 문서 내용이 필요하면 링크(또는 "DATA_MODEL 2.5절"처럼 절 번호)로 가리킨다
- 아직 코드가 없는 설계는 **문서가 먼저**, 코드가 원본인 것은 코드가 먼저다. 설계를 바꾸면 같은 작업 안에서 문서도 맞춘다
- 문서의 장 · 절 번호를 바꾸면 그 번호를 부르는 자리를 검색해서 같이 고친다
- DEVLOG의 지난 기록은 고치지 않고 위에 새 항목을 덧붙인다. `archive/`도 고치지 않는다 (옛 문서 이름은 archive/README 대응표)

## 시작할 때
1. `git pull`
2. [`docs/DEVLOG.md`](docs/DEVLOG.md) "현재 상태"를 읽는다
3. 하려는 일에 맞는 문서를 위 지도에서 골라 본다

## 끝날 때
- DEVLOG "현재 상태"를 고친다 (완료 / 진행 중 / 다음에 할 일)
- 겪은 문제 · 결정은 **그 세션 안에서** DEVLOG에 적는다. 형식은 전역 "문서 체계"와 DEVLOG 위쪽 "작성 규칙"을 따른다. 막혔던 점은 해결됐어도 남긴다
- 끝낸 항목은 PLAN 작업 목록 체크박스와 2장 진행 현황 표에 반영한다. 계획에 없던 작업은 `*(계획에 없던 작업)*`을 붙여 추가한다
- **마일스톤을 ✅로 닫기 전에 PLAN만 보지 않는다.** PLAN 작업 목록은 빠질 수 있다(2026-11-04: F-03 정렬 · 장르 필터가 M2 ~ M4 어디에도 없어 놓쳤다). 그 단계까지의 버전에 속한 `REQUIREMENTS` 4장 기능 · 6장 비기능, `DESIGN` 화면 규격 표, 목업을 코드와 항목별로 대조해 표로 DEVLOG에 남긴다. 빠진 것은 PLAN에 넣어 끝내거나, 일부러 미루면 어느 단계로 미루는지 PLAN에 적고 사용자에게 알린다

## 작업 규칙
- **전역 설정 위치**: 모든 기기(회사 PC · 집 PC · 노트북) `~/.claude/CLAUDE.md`
- **말투**: 대화 말투는 전역 설정을 따른다. 문서 · 주석 · 커밋 메시지는 지금 저장소의 문체를 따른다
- **작업 방식**: 기본은 전역 설정의 "작업 방식" 절이다(자동 / 타이핑 학습 모드 / 사용자가 직접 치는 것 / 구현 전 사전 검증 / 검증). 여기에는 PlayLedger에만 해당하는 세부만 적는다 (2026-11-02부터)
  - **전역 작업 방식과 다르게**: 코드를 쓰는 본격 작업(마일스톤 작업 항목, 기능 추가)에 들어가기 전에는 "자동으로 할까, 직접 칠래?"를 **반드시** 한 줄로 물어본다(전역은 "물어봐도 된다"). 이미 정해 줬으면 묻지 않는다. 2026-10-24부터 이 저장소에서 지켜 온 규칙을 유지한다
  - 사전 검증에서 따라갈 시나리오에 **동시 실행**(토큰 재발급 · 같은 게임 · 장르 동시 생성)을 꼭 넣는다 — 이 저장소의 함정 · 테스트가 여기에 몰려 있다
  - 보고에는 설계한 진행 순서도 넣는다
- **주석**: 기존 코드처럼 한국어로, "왜 이렇게 했나"와 비유를 곁들인다. 문서를 근거로 삼은 줄에는 `(DATA_MODEL 2.4절)`처럼 출처를 단다
- **범위**: 새 기능 아이디어가 떠오르면 바로 구현하지 않고 `REQUIREMENTS` 4.4절에 항목만 추가한다. 범위를 일부러 넓힐 때는 사유를 `decisions/`나 DEVLOG `[설계]`에 남긴다
- **검증**: 원칙(관찰값을 남긴다)은 전역 "작업 방식"을 따른다. PlayLedger에서는 네트워크 탭 기록도 관찰값으로 남긴다
  - 서버를 고쳤으면 `pytest`, 프론트를 고쳤으면 `npm run lint` · `npm run format:check` · `vue-tsc -b --noEmit` · `npm test`를 돌린다
  - 응답 본문의 모양은 코드에 적혀 있지 않다. 문서에 JSON을 옮길 때는 Swagger `Execute`로 실제 응답을 받아 옮긴다

## 브랜치 · 커밋 · 푸시
- **2026-10-24부터 브랜치를 따로 파지 않고 `main`에서만 작업한다.** M0 · M1은 PR(#1 · #2)로, M2 앞부분은 `m2-frontend` PR로 병합됐다
- **자동 모드**에서 작업과 검증을 마쳤으면 커밋하고 `git push`까지 한다. 타이핑 학습 모드에서는 사용자가 직접 커밋한다
- 검증이 실패했거나 끝나지 않은 작업은 커밋하지 않고 상태를 알린다. `git push --force`, 히스토리 수정은 하지 않는다
- 의미 단위로 나눠 커밋한다 (서버 · 테스트 · 프론트 · 문서, 동작이 바뀌는 수정은 따로)
- 메시지는 **Summary + Description** 구조로 쓴다

  ```text
  feat(M2): auth 스토어

  - Pinia 4.0.3 도입 및 main.ts 등록 (router보다 먼저)
  - stores/auth.ts ─ user · isReady 상태, login · register · logout
  - access 토큰은 스토어가 보관하지 않고 client.ts에 위임
  ```

  - Summary(첫 줄): `종류(마일스톤): 한국어 요약`. 종류는 `feat` · `fix` · `refactor` · `test` · `docs` · `chore` · `ci`
  - 빈 줄 하나 뒤 Description: `- ` 목록으로 무엇을 · 왜 바꿨는지, 확인한 결과(테스트 건수 등)를 적는다. 동작 변경이 없으면 그렇게 적는다

## 함정 (고치기 전에 확인)
- **DB 주소 형식**: `server/.env`의 `DATABASE_URL` · `TEST_DATABASE_URL`은 `postgresql+asyncpg://...@localhost:5434/...`이다. `+asyncpg`가 빠지면 `No module named 'psycopg2'`로 서버가 안 뜨고, Vite에는 `http proxy error ... ECONNREFUSED`만 보인다
- **DB 비밀번호**: `postgres` 컨테이너는 볼륨을 **처음 만들 때만** 루트 `.env`의 `POSTGRES_PASSWORD`를 읽는다. 나중에 `.env`만 바꾸면 `InvalidPasswordError`가 난다. 루트 `.env`와 `server/.env`의 `DATABASE_URL` · `TEST_DATABASE_URL` 세 곳의 비밀번호가 같아야 한다
- **테스트 DB**: 기기마다 `playledger_test`를 한 번 만들어야 한다 (README "시작하기"). 이름이 `_test`로 끝나지 않으면 `conftest.py`가 테스트를 시작하지 않는다
- **테스트 클라이언트는 `https://test`**: refresh 쿠키가 `Secure`라서 http로 부르면 쿠키가 실리지 않는다
- **재발급 동시 요청 금지**: refresh는 rotation이라 동시에 두 번 보내면 재사용 감지가 정상 사용자를 로그아웃시킨다. 클라이언트는 재발급을 한 번만 보내고 나머지는 기다린다 (ARCHITECTURE 3.3절)
- **422 본문은 두 형태**: Pydantic이 만든 422는 `detail`이 배열, 서버가 직접 던진 422는 문자열이다. 500의 `detail`은 영문이다. 화면에는 `web/src/api/errors.ts`를 거쳐 보여 준다 (ARCHITECTURE 3.9절)
- **남의 기록은 403이 아니라 404**: "없는 것"과 "남의 것"의 응답 본문이 같아야 한다 (ARCHITECTURE 3.8절)
- **날짜와 시각**: `created_at`은 UTC 시각(`...Z`), `purchased_at`은 날짜(`YYYY-MM-DD`)다. 날짜를 시각 파서로 읽으면 한국 시간으로 하루 전날이 된다
- **async SQLAlchemy**: 응답에 쓰는 관계(`entry.game`, `game.genres`)는 `selectinload`로 미리 불러온다. lazy load가 안 된다
- **반응형 기준은 `48rem`**: px이 아니라 루트 글꼴 크기에 따라 기기마다 전환 지점이 다르다

## 하지 말 것
- `npx shadcn-vue add`를 그대로 치지 않는다. `style.css`와 패키지 버전을 바꾸고 고쳐 둔 `button`을 덮어쓰려 한다. 레지스트리의 소스만 받아 import를 `@/lib/utils` · `@/components/ui`로 바꿔 넣는다 (DEVLOG 2026-11-04 (8))
- `.env`(루트 · `server/`)를 커밋하지 않는다. `STEAM_API_KEY`는 화면 · 로그 · URL에 찍지 않는다 (헤더로만 보낸다)
- `alembic.ini`에 한글을 쓰지 않는다 (Windows에서 cp949로 읽어서 `UnicodeDecodeError`가 날 수 있다). DB 주소도 넣지 않는다 (`alembic/env.py`가 `.env`에서 읽음)
- access 토큰을 `localStorage`에 넣지 않는다. 메모리(`api/client.ts`)에만 둔다

## 기기 3대
- 코드는 GitHub로만 주고받는다 (`git pull` → 작업 → `git push`)
- `.env`, `venv/`, `node_modules/`, DB 데이터는 Git에 없으므로 기기마다 따로 준비한다 (`.env.example` 참고)
- DB 구조는 Alembic으로 맞춘다: `git pull` 후 항상 `alembic upgrade head`
  - 마이그레이션 파일은 **모델을 고친 기기에서만** 만든다. 파일명은 `alembic.ini`의 `file_template` 규칙(`날짜_시각_설명`)을 따른다
  - autogenerate 결과는 그대로 믿지 말고 읽어 보고, `alembic upgrade head --sql`로 실제 SQL을 확인한 다음 커밋한다
- 패키지를 추가하거나 버전을 올렸으면 `requirements.txt` · `package-lock.json`을 같이 커밋하고, 다른 기기에서 할 일(`pip install -r requirements.txt`, `npm ci`)을 DEVLOG "현재 상태"에 적는다

## 자주 쓰는 명령
포트: DB `5434` · API `8001` · 프론트 `5173`

```powershell
# 루트
docker compose up -d                              # PostgreSQL

# server/ (가상환경: .\venv\Scripts\Activate.ps1)
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8001         # http://localhost:8001/docs
pytest                                            # 테스트 전용 DB 사용
python -m app.scripts.sync_steam_apps             # Steam 게임 목록 미러링 (STEAM_API_KEY 필요, 비어 있어도 서버는 뜬다)
python -m app.scripts.seed_demo --email 나@example.com  # 예시 게임 26개 (로컬 DB의 빈 계정에만, 기대값은 tests/test_stats.py)

# web/
npm ci
npm run dev                                       # http://localhost:5173 (/api는 8001로 프록시)
npx vue-tsc -b --noEmit; npm test                 # 타입 검사 · Vitest
npm run lint; npm run format:check                # ESLint · Prettier 검사 (npm run format이 모양을 고친다)
```
