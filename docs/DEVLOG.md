# PlayLedger — DEVLOG

> 세션별 개발 회고 및 트러블슈팅 기록

이 문서는 마일스톤 문서(`05_milestones.md`)처럼 "계획"을 담는 곳이 아니라,
**실제로 각 세션에서 무슨 일이 있었는지**를 기록하는 곳이다.
막혔던 지점, 해결한 방법, 다음에 참고할 만한 실수 등을 가감 없이 남긴다.

---

## 현재 상태

**진행 중** · M1 (백엔드 기초) — 모델 6종 · 마이그레이션 4건 · 인증 전 항목 · 장르 시드 · 정규화 규칙(`core/normalize.py`) · 게임 조회 · 생성 서비스(`find_or_create_game`) · 장르 목록 API · 장르 연결 서비스 · **보유 기록 CRUD 전체** 완료. 테스트 · CI · API_SPEC 남음

**환경 요약**
| 항목 | 값 |
|---|---|
| Python | 데스크톱 A ─ 3.13.5 · 데스크톱 B/노트북 ─ 3.13.9 (Anaconda 빌드). 3.13 안에서는 차이 없음 |
| Node.js | v24.15.0 |
| FastAPI · Uvicorn | 0.141.1 · 0.53.0 |
| SQLAlchemy · asyncpg | 2.0.54 · 0.31.0 |
| Alembic | 1.20.0 (async 템플릿, 마이그레이션 4건 · head `1e1d15e51ba2`, 파일명 `날짜_시각_설명`) |
| argon2-cffi | 25.1.0 (Argon2id, 비밀번호 해싱) |
| PyJWT | 2.14.0 (access 토큰 서명, HS256) |
| Vue · Vite · TypeScript | 3.5.42 · 8.3.0 · 6.0.2 |
| Tailwind CSS · shadcn-vue | 4.3.3 · 2.8.2 (컴포넌트 미추가) |
| PostgreSQL | 18.6 (`postgres:18` 컨테이너, 테이블 7개 — v1.0 범위 6종 + `alembic_version`) |
| HeidiSQL | PostgreSQL 접속 가능한 버전 (데스크톱 B 12.21. 기기마다 버전이 달라도 무방) |
| Docker · Compose | 29.8.0 · v5.5.1 |
| 포트 | DB `5434` · API `8001` · 프론트 `5173` |
| 이전 버전 | `v0-rn-django` 태그 (RN 0.87.0 + Django 6.1 + MariaDB 12.2.2) |
| 대상 | 웹 (데스크톱 · 모바일 브라우저) |

**실행 방법** · 터미널 3개 — 프로젝트 루트에서 `docker compose up -d` / `server`에서 `uvicorn app.main:app --reload --port 8001` / `web`에서 `npm run dev`

**다음에 할 일** · pytest 환경 구성(테스트 전용 DB) → 사용자 격리 · 중복 판별 · 장르 연결 동시 실행 · 토큰 테스트 → GitHub Actions → `06_api_spec.md` → M1 완료 처리 및 PR

---

## 작성 규칙

- 세션(하루 작업 단위) 종료 시 또는 마일스톤 완료 시 기록
- 최신 항목이 위로 오도록 역순 정렬
- 형식: 날짜 / 관련 마일스톤 / 한 일 / 결정 기록 / 막혔던 점 / 다음에 할 일 (결정 기록은 판단이 있었던 세션만)
- 기기 표기는 `README` 개발 환경 표를 따른다 (데스크톱 A · 데스크톱 B · 노트북)

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

## 2026-09-23(점심~오후/데스크톱 A) — M1 진행 중: 보유 기록 CRUD 완성, 테스트 · CI · API_SPEC 남음

**관련 마일스톤**: M1 (백엔드 기초) → 진행 중

**한 일**
- ERD v1.7 · UI_DESIGN v1.4 — 보유 기록의 `game_id`를 바꾸지 않는다는 규칙 추가. **코드보다 먼저** 고침
- `app/services/entry.py` — `list_entries`(상태 필터 · 페이지네이션 · 전체 개수 동반 반환), `MAX_LIMIT = 100`
- `app/schemas/entry.py` — `EntryListResponse`(`items` + `total`), `EntryUpdate`(전 항목 선택, `title`은 받지 않음)
- `app/routers/entries.py` — 엔드포인트 4개 추가
  - `GET /api/entries` — `?status` · `limit` · `offset`, 최근 수정순(`updated_at DESC, id DESC`)
  - `GET /api/entries/{id}` · `PATCH` · `DELETE` — 없거나 남의 것이면 전부 404
  - PATCH는 `model_dump(exclude_unset=True)`로 보낸 항목만 반영, `status` · `playtime_minutes`에 null이 오면 422
  - DELETE는 204, `games`는 건드리지 않음
- 이 기기에 검증용 데이터 준비 (계정 B 생성 + 기록 3개). DB는 기기마다 달라 노트북 데이터가 없음
- Swagger 검증 20건
  - 목록 8건 — `total: 3`, `?status=BACKLOG` → 2, `?status=CLEARED` → `{"items": [], "total": 0}`(404 아님), `?limit=1`에도 `total: 3` 유지, `?limit=0` 거부
  - 단건 — A 200 / **B가 A의 id 조회 → 404** / 없는 id → 404. 두 404가 `content-length: 46`으로 동일
  - 수정 12건 — `{"status": "CLEARED"}` 한 줄에 나머지 5개 필드 보존, `{}` → 변경 없음(`updated_at`도 유지), `{"rating": null}` → 지워짐, `{"status": null}` → 422, `{"title": ...}` → 422 `extra_forbidden`, `{"rating": 9}` → 422
  - 장르 — 장르 0개 게임에 `genre_ids` → 채워짐 / 이미 있는 게임에 다른 장르 → 무시
  - 삭제 — 204 → 재요청 404 → 목록 `total: 2`, HeidiSQL에서 `games`에 해당 게임(id 4) **잔존 확인**

**결정 기록**
- **보유 기록의 제목(= `game_id`)은 수정할 수 없다** (ERD v1.7 · UI_DESIGN v1.4)
  제목을 바꾸는 것은 이 기록이 가리키는 게임을 갈아끼우는 것이라, 쌓인 플레이타임 · 평점 · (v2.0의) 플레이 세션이 엉뚱한 게임에 붙는다. 허용하면 "바꾼 게임을 이미 등록했으면 409", "아무도 안 쓰는 게임이 `games`에 고아로 남음" 같은 가지가 줄줄이 생긴다. 잘못 등록한 게임은 삭제 후 재등록으로 해결되고, v1.0은 입력 항목이 적어 다시 치는 비용이 작다. 조용히 무시하지 않고 422로 거절 — `EntryCreate`의 `extra="forbid"`와 같은 이유
- **목록은 `items`와 `total`을 함께 돌려준다**
  20개만 받으면 화면은 "더 있는지"를 알 수 없다. 개수 조회와 목록 조회가 같은 `conditions` 변수를 쓰도록 해, 한쪽에만 필터를 빠뜨려 "3개인데 전체 10개"가 되는 일을 막았다
- **정렬 기준을 `updated_at DESC, id DESC` 두 개로**
  `updated_at`이 같은 행끼리는 순서가 매번 달라질 수 있어, 1페이지와 2페이지에 같은 기록이 겹치거나 빠진다. id를 두 번째 기준으로 두면 순서가 고정된다
- **`limit`에 상한(100)을 둔다**
  상한이 없으면 `limit=999999`로 DB를 통째로 긁어갈 수 있다. 화면은 20개씩 불러오므로(UI_DESIGN 3.2절) 100이면 충분하다
- **PATCH 스키마의 `None`은 "안 보냄"이고, 라우터가 NOT NULL 컬럼의 null을 따로 막는다**
  `EntryUpdate`는 전 항목이 `| None = None`이라 스키마만으로는 "생략"과 "null 전송"을 구분할 수 없다. `exclude_unset=True`가 생략을 걸러내므로, 그러고도 남은 `None`은 사용자가 명시적으로 적어 보낸 null이다. DB에 넣으면 500이 나므로 라우터에서 422로 거절한다

**막혔던 점 / 트러블슈팅**
- 증상: PATCH 검증 1번에서 `{"status": "PLAYING"}`만 바꾸려 했는데, Swagger가 채워준 예시 본문을 그대로 실행해 전 필드를 보냄
  - 원인: Swagger의 Request body는 스키마의 모든 필드가 채워진 예시로 시작한다. 그대로 실행하면 PATCH인데 사실상 PUT처럼 전송된다
  - 해결: 본문을 통째로 지우고 `{"status": "CLEARED"}` 한 줄만 남겨 재검증. 나머지 5개 필드가 보존되는 것을 확인
  - 교훈: **검증 방법이 검증 대상을 무력화할 수 있다.** 전부 보내면 전부 바뀌므로 "안 보낸 값이 유지되는가"를 확인할 수 없다. 09-21의 "길이 초과 예시가 사실 초과가 아니었던" 건과 같은 계열 — 코드가 아니라 검증 설계가 틀린 경우
- 증상: 검증 도중 갑자기 401 `인증이 필요합니다`
  - 원인: access 토큰 수명 15분이 지남. 자리를 비운 사이 만료됨
  - 해결: 재로그인 후 Authorize에 새 토큰
  - 교훈: 09-23 오전 노트북 세션의 401 연속 발생도 같은 원인이었다. 손 검증이 길어지면 반드시 겪는다

**배운 것**
- Swagger UI는 OpenAPI 스키마에 실린 제약(`minimum` 등)을 보고 **요청을 보내기 전에** 막는다. `?limit=0`은 서버까지 가지 않고 브라우저에서 거부됐다(Curl 박스가 안 생긴 것이 증거). 서버 쪽 422를 직접 보려면 주소창으로 요청해야 한다
- `{}`를 보내면 `changes`가 비어 `setattr` 루프가 한 번도 돌지 않고, SQLAlchemy가 UPDATE문 자체를 만들지 않아 `onupdate`도 걸리지 않는다. 실제로 `updated_at`이 그대로였다 — "아무것도 안 바꿈"이 진짜로 아무것도 건드리지 않는다
- `RESTRICT`의 의도가 삭제 검증에서 드러났다. entry는 사라졌지만 `games`의 해당 행은 남는다. 지금은 혼자 써서 고아처럼 보이지만, 다른 사용자가 그 게임을 참조하고 있을 수 있으므로 이것이 맞다
- DB 데이터는 Git으로 동기화되지 않는다. 마이그레이션 파일을 반드시 커밋하는 이유가 이것 — 데이터는 안 따라가도 "구조를 만드는 순서"는 따라간다. 기기를 옮길 때마다 손 검증용 데이터를 다시 만들어야 하는 것이 그 대가다

**발견 사항 (지금 조치하지 않음)**
- 손으로 하는 Swagger 검증이 기기 이동의 실질적 비용이다. 오늘만 27건(장르 8 · 등록 7 · 조회 8 · 수정 삭제 12)을 클릭했고, 계정 · 기록 준비와 토큰 만료 대응이 매번 따라붙는다. pytest로 옮기면 테스트 DB가 매번 비워진 상태로 시작해 준비 과정이 사라지고, 기기 성능 · 화면 크기와 무관해진다. M1의 "테스트 · CI" 섹션이 이 문제를 그대로 푼다

**다음에 할 일**
- pytest 환경 구성 (테스트 전용 DB) → 오늘까지의 손 검증을 코드로 이관
- 사용자 격리 · 게임 중복 판별(동시 등록 포함) · 장르 연결 동시 실행 · 토큰 만료 · rotation 테스트
- GitHub Actions → `06_api_spec.md` → M1 완료 처리 후 PR

---

## 2026-09-23(오전/노트북) — M1 진행 중: 보유 기록 등록 API 구현, 목록 · 단건 · 수정 · 삭제 남음

**관련 마일스톤**: M1 (백엔드 기초) → 진행 중

**한 일**
- `app/services/entry.py` 신설
  - `get_entry` — `(entry_id, user_id)` 두 조건으로 조회, `selectinload`로 게임 · 장르 동반 로딩, `populate_existing=True`
  - `entry_exists` — 같은 사용자의 같은 게임 등록 여부 (중복 1차 방어)
  - 두 함수 모두 `*`로 `user_id`를 키워드 전용 인자로 강제
- `app/routers/entries.py` 신설 — `POST /api/entries`
  - ① 장르 id 검증(422) → ② `find_or_create_game` → ③ 중복 409 → ④ `attach_genres_if_empty` → ⑤ entry 생성 · commit → ⑥ `get_entry`로 재조회 후 201
  - `IntegrityError`를 제약 이름(`uq_entries_user_id_game_id`)으로 판별해 409, 그 외는 그대로 전파
  - `user_id` · `game_id` · `source`는 요청이 아니라 서버가 채움
- `main.py`에 entries 라우터 등록
- Swagger 검증 7건 (계정 2개로 교차)
  - A `Hollow Knight` + 액션 → 201, `source: MANUAL`
  - A `"  hollow knight  "` → 409 (공백 · 대소문자 정규화 확인)
  - A 장르 `9999` → 422, A `Celeste` 장르 없음 → 201 `genres: []`
  - B `Celeste` + RPG → 201, **같은 게임에 장르가 채워짐** (0개였으므로)
  - B `HOLLOW KNIGHT` + 전략 → 201, `genres: [액션]` **입력 무시**, `title`은 A가 등록한 `Hollow Knight` 유지
  - A `source: "STEAM"` 전송 → 422 `extra_forbidden`

**결정 기록**
- **중복 확인(③)을 장르 연결(④)보다 앞에 둠**
  어차피 409로 거절할 요청이 게임 행을 `FOR UPDATE`로 잠그면, 통과할 다른 요청만 그만큼 기다린다. 거절할 것은 잠그기 전에 거절한다
- **`IntegrityError`를 전부 409로 바꾸지 않고 제약 이름으로 구분**
  `IntegrityError`는 UNIQUE뿐 아니라 CHECK · FK 위반에서도 발생한다. 전부 "이미 등록된 게임입니다"로 바꾸면 진짜 버그가 그 메시지 뒤에 숨는다. 09-19에 `naming_convention`을 먼저 정해둔 것이 여기서 쓰였다
- **`title` 수정 허용 여부는 보류**
  제목을 바꾼다는 것은 `entries.game_id`를 다른 게임으로 갈아끼우는 것이라, 그 기록에 쌓인 플레이타임 · 평점이 엉뚱한 게임에 붙는다. 수정 API 구현 시 함께 결정한다

**막혔던 점 / 트러블슈팅**
- 증상: (실행 전 검수에서 발견) `EntryCreate` · `EntryRead`의 필드명이 `purchase_price`가 아닌 `purchased_price`
  - 원인: 바로 위 `purchased_at`의 `d`가 옮겨붙음. 문법상 유효한 이름이라 에디터도 파이썬도 잡지 않는다
  - 해결: 두 곳 모두 정정
  - 교훈: 터지는 곳이 셋으로 갈린다 — 응답 생성 시 500, 프론트가 **올바른** 이름을 보내면 `extra_forbidden` 422, 모델 생성 시 `TypeError`. 특히 두 번째는 서버가 맞는 요청을 거절하므로 프론트 버그로 오인하기 쉽다
- 증상: (실행 전 검수에서 발견) `get_entry`의 `.option(...)`, `.execute_options(...)`
  - 원인: 올바른 이름은 `.options()`, `.execution_options()`
  - 해결: 정정
  - 교훈: 메서드 이름 오타는 정의 시점이 아니라 **그 함수를 처음 호출할 때** `AttributeError`로 드러난다. 다만 에러 메시지에 틀린 이름이 그대로 찍혀 원인 추적은 쉽다 — 위의 필드명 오타보다 나은 종류

**배운 것**
- 비동기 SQLAlchemy는 지연 로딩(lazy load)을 못 한다. `entry.game`에 접근하는 순간 몰래 조회하는 동작이 `MissingGreenlet`으로 막히므로, 응답에 쓸 관계는 `selectinload`로 미리 불러와야 한다
- `selectinload`는 JOIN 한 방이 아니라 쿼리 3번(entries / games / genres)으로 나눠 실행한다. 기록이 20개여도 쿼리 수가 3으로 고정되어 N+1을 피한다
- `expire_on_commit=False`는 commit 후에도 객체 값을 유지하지만, 그 값은 **옛 값**이다. `insert()`로 DB만 바꾼 `game_genres`는 파이썬 객체가 모르므로 `populate_existing=True`로 최신 값을 다시 읽어야 한다
- Pydantic은 기본이 느슨한 모드(lax)다. `playtime_minutes`에 문자열 `"99999999999"`를 보내도 정수로 변환한 뒤 범위를 검사한다. 폼 입력이 문자열로 오는 경우를 흡수해준다

**다음에 할 일**
- 보유 기록 목록 · 단건 · 수정 · 삭제 — 남의 기록 요청은 403이 아니라 404
- 수정 API 착수 전 `title` 수정 허용 여부 결정
- pytest 환경 구성 → 사용자 격리 · 중복 판별 · 장르 연결 동시 실행 테스트

---

## 2026-09-22(저녁~밤/데스크톱 A → 노트북) — M1 진행 중: 장르 목록 API, 관계 · 스키마, 장르 연결 서비스

**관련 마일스톤**: M1 (백엔드 기초) → 진행 중

**한 일**

*데스크톱 A (저녁)*
- `app/schemas/genre.py` — `GenreRead`(`id` · `name`만, `steam_genre_id` 제외)
- `app/routers/genres.py` — `GET /api/genres`, 라우터 전체에 `dependencies=[Depends(get_current_user)]`
- Swagger 검증 — 토큰 없이 401, 로그인 후 8개 · ERD 표 순서, 응답에 `steam_genre_id` 없음(`content-length: 222`로 대조)
- `models/game.py` — `Game.genres` relationship (`secondary=game_genres`, `order_by="Genre.id"`)
- `models/entry.py` — `Entry.game` relationship, `TYPE_CHECKING`으로 순환 참조 회피
- `alembic check` → `No new upgrade operations detected.` (relationship은 DB를 바꾸지 않음을 확인)
- `app/schemas/game.py` — `GameRead`(`id` · `title` · `genres`)
- `app/schemas/entry.py` — `EntryCreate` / `EntryRead`, `EntryStatus` Literal, `INT_MAX` 상한
- REPL 검증 5건 — 공백 제거 · 기본값, `"!!!"` 거부, `extra_forbidden`, 정수 상한, `literal_error`

*노트북 (밤)*
- `app/services/genre.py` — `genre_ids_exist`(없는 장르 id 검사), `attach_genres_if_empty`(0개일 때만 연결)
- 임시 스크립트로 동시 실행 검증 (확인 후 삭제, 커밋하지 않음)
  - `FOR UPDATE` 있음 → 후발 요청이 **2.5초 대기 후 무시**, 최종 장르 1개
  - `FOR UPDATE` 제거 → 후발 요청이 **0.1초에 통과**, 최종 장르 2개로 **합쳐짐**

**결정 기록**
- **게임의 장르는 0개일 때만 채운다** (ERD v1.6 · UI_DESIGN v1.3, 코드보다 먼저 문서 수정)
  `games`는 모든 사용자가 공유하는 마스터 데이터다. ①덮어쓰기는 먼저 등록한 사용자의 장르별 통계(F-11)를 본인 모르게 바꾸고, ②합치기는 누구든 장르를 추가만 할 수 있어 잘못된 입력이 모두의 통계에 영구히 남는다. 그렇다고 ③"새 게임일 때만 연결"로 두면, 장르가 선택 항목(S-03)이라 비워둔 채 등록한 게임에 **나중에 장르를 붙일 경로가 없다**. 그래서 "아무도 정하지 않은 빈칸만 채운다"로 확정. 잘못 붙은 장르 수정은 관리자 권한(F-23)으로 미룸. v0 admin 화면에서 `title_norm`이 오염된 사건과 같은 계열 — 공유 데이터를 개별 사용자의 입력이 건드리는 문제
- **장르 수를 세기 전에 게임 행을 잠근다 (`SELECT ... FOR UPDATE`)**
  "0개인지 확인 → 채우기" 사이의 틈은 `title_norm` 부분 UNIQUE로 막을 수 없다. "장르가 0개여야 한다"는 행 하나의 규칙이 아니라 **개수** 규칙이라 DB 제약으로 표현되지 않는다. 잠금이 유일한 수단이고, 위 실측이 그 차이를 보여준다
- **`find_or_create_game`의 반환값을 `(game, created)`로 바꾸지 않음**
  처음엔 "방금 만든 게임인지"를 알아야 한다고 판단했으나, 새 게임은 장르가 당연히 0개이므로 "0개면 채운다" 한 규칙이 신규 · 기존을 모두 처리한다. 기존 시그니처를 유지하고 함수만 하나 추가
- **장르 목록 API는 로그인 필요**
  비밀 정보는 아니지만, 이 API를 쓰는 화면(S-03)은 어차피 로그인 뒤에 있다. "`/api/auth` 외에는 전부 로그인 필요"가 "대부분 필요, 단 장르는 예외"보다 기억하기 쉽고, 예외는 나중에 잊는 사람이 실수하는 자리다
- **장르 목록 정렬은 `id`순**
  `steam_genre_id`는 문자열이라 정렬하면 `"18"`이 `"2"`보다 앞에 온다. 09-21에 "id 숫자로 장르를 가리키지 말 것"을 배웠지만 그것은 **특정 장르를 지목**할 때의 이야기이고, 전체를 **한 번에 나열**하는 순서로는 id가 시드 입력 순서를 그대로 보존한다
- **`EntryCreate`에 `extra="forbid"`**
  Pydantic 기본값은 정의되지 않은 필드를 조용히 버린다. 그러면 `source: "STEAM"`을 보낸 쪽은 "보냈는데 왜 반영이 안 되지?"를 알 수 없다. 거부하면 그 자리에서 드러난다
- **평점과 상태의 조합을 서버가 막지 않음**
  `BACKLOG`에 `rating`이 와도 통과시킨다. UI_DESIGN 4.3절이 "재플레이해도 평점은 지우지 않고 숨긴다"이므로, 서버가 "PLAYING엔 평점 금지"를 걸면 그 규칙과 충돌한다. 보이고 안 보이고는 화면의 몫

**막혔던 점 / 트러블슈팅**
- 증상: `alembic current`가 `.\alembic\ : 용어가 cmdlet, 함수... 로 인식되지 않습니다`
  - 원인: 탭 자동완성이 같은 이름의 **폴더**(`alembic/`)를 잡아 `.\alembic\`로 바뀜. 실행하려던 것은 venv에 설치된 **명령어** `alembic`
  - 해결: 경로 없이 `alembic current`
  - 교훈: 폴더명과 명령어 이름이 같으면 자동완성이 폴더를 우선한다
- 증상: `git add renormalize .`가 `pathspec 'renormalize' did not match any files`
  - 원인: `--`가 빠져 옵션이 아닌 **파일 이름**으로 해석됨
  - 해결: `git add --renormalize .`
  - 교훈: 새로 만든 파일은 `.gitattributes` 규칙이 `git add` 때 적용되므로 `--renormalize`가 필요 없다. 이 옵션은 **이미 커밋된** 파일을 규칙에 맞춰 다시 정리할 때 쓴다

**배운 것**
- relationship은 DB 구조를 바꾸지 않는다. 테이블 · 컬럼은 그대로이고 파이썬 쪽에 "따라가는 길"만 생긴다. `alembic check`가 이를 증명하는 수단이 된다
- PostgreSQL 기본 격리 수준(READ COMMITTED)에서는 **SQL 문장 단위로** 그 시점에 commit된 최신 데이터를 본다. 잠금을 기다린 뒤 실행되는 COUNT는 새 문장이므로, 먼저 commit한 쪽의 결과가 보인다
- `game_genres`는 ORM 클래스가 아니라 `Table` 객체라 컬럼을 `.c.game_id`로 꺼낸다
- 비동기에서는 `game.genres.append()`를 쓸 수 없다. 목록을 먼저 불러와야 하는데 지연 로딩이 막혀 있어, 연결 테이블에 `insert()`로 직접 넣는다

**다음에 할 일**
- 보유 기록 등록 API — 장르 검증 → 게임 조회 · 생성 → 중복 409 → 장르 연결 → commit → 재조회
- 작업 기기를 노트북에서 이어감 (`git pull` → `alembic current` 확인)

---

## 2026-09-22(오후/데스크톱 B) — M1 진행 중: 문서 참조 표기 통일 및 장르 연결 규칙 설계

**관련 마일스톤**: M1 (백엔드 기초) → 진행 중

**한 일**
- 전 문서의 상호 참조 표기를 번호에서 이름 기준으로 통일 (`01~05 문서` → `REQUIREMENTS` · `ARCHITECTURE` · `ERD` · `UI_DESIGN` · `MILESTONES`)
- 게임 CRUD 착수 전 설계 점검에서 "공유 데이터인 `games`의 장르를 누가 정하는가"가 미정임을 발견
- ERD v1.6 — 2.5절에 **장르 연결 규칙** 신설 (상황별 동작 표, 행 잠금, F-23으로 이관할 범위)
- UI_DESIGN v1.3 — 3.3절 규격 표에 "장르 (수정 모드)" 행 추가

**결정 기록**
- **설계 구멍은 코드를 짜기 전에 문서로 먼저 메운다**
  `find_or_create_game`까지 만들어 놓고 등록 API로 넘어가려는 시점에, 기존 게임에 장르 입력이 들어오면 어떻게 되는지가 어느 문서에도 없었다. 구현하면서 정했다면 그 판단이 코드에만 남고 근거는 사라졌을 것이다. 결정 내용은 다음 세션 기록(09-22 저녁~밤) 참고

**막혔던 점 / 트러블슈팅**
- 증상: (문서 검수에서 발견) UI_DESIGN 3.3절에 행을 **추가**하려다 기존 `수정 모드` 행을 덮어씀
  - 원인: 새 행의 라벨을 `장르 (수정 모드)`로 잡으면서 기존 행의 내용까지 그 뒤에 이어 붙임. 결과적으로 "수정 화면은 등록 화면을 재사용한다"는 규격이 장르 항목의 일부처럼 읽히게 됨
  - 해결: 두 행으로 분리
  - 교훈: 09-18의 "`git diff`로 삭제된 줄(`-`)을 훑는다"가 잡으라고 있는 유형. 표에 행을 추가할 때는 기존 행 수가 늘었는지 확인한다
- 증상: (문서 검수에서 발견) UI_DESIGN 변경 이력에 "동시 요청 대비 게임 행 잠금"이 들어감
  - 원인: ERD 변경 이력을 복사해 옴. 그 문서에서 실제로 바뀐 것보다 많은 내용을 주장하게 됨
  - 해결: 해당 문서에서 바뀐 것만 남기고 상세는 ERD 참조로
  - 교훈: 변경 이력은 그 문서에서 바뀐 것만 적는다. 같은 결정이라도 문서마다 바뀐 부분이 다르다

**다음에 할 일**
- 장르 목록 조회 API → 관계 · 스키마 정의 → 장르 연결 서비스 → 등록 API
- Project Knowledge에 옛 `docs/05_milestones.md`(체크박스가 전부 빈 버전)가 남아 있어 재업로드 시 정리 필요

---

## 2026-09-22(오전/노트북 → 데스크톱 B) — M1 진행 중: 게임 조회 · 생성 서비스 구현, wip 커밋을 force push로 대체

**관련 마일스톤**: M1 (백엔드 기초) → 진행 중

**한 일**
- ERD v1.4 — 판별 2단계의 조회 범위를 수동 등록 게임(`steam_appid IS NULL`)으로 명시. **코드보다 먼저** 고침
- `app/services/__init__.py`, `app/services/game.py` 신설
  - `_find_game` — 1단계(`steam_appid`) · 2단계(수동 게임 중 `title_norm`) 조회
  - `find_or_create_game` — 없으면 SAVEPOINT(`begin_nested`) 안에서 INSERT + `flush`, `IntegrityError`면 재조회(4단계), 재조회도 실패하면 원래 에러를 다시 던짐
  - `title_norm`은 호출한 쪽을 믿지 않고 서비스에서 직접 계산. commit은 하지 않음
- 노트북에서 절반 작성 → `wip` 커밋(`8d44d7c`) push → 데스크톱 B에서 pull → `git reset HEAD~1` → 나머지 작성
- asyncio REPL 검증
  - `"Hollow Knight"` / `"  hollow  KNIGHT "` 두 번 호출 → `1 1 Hollow Knight` (같은 행 재사용, 먼저 적은 제목 유지)
  - 세션 2개로 `"Celeste"` / `"celeste!"` 동시 호출(`asyncio.gather`) → `[2, 2]`
  - HeidiSQL에서 2행 확인 후 삭제
- wip 커밋을 docs(`ae061e7`) · feat(`0d4ed14`) 두 커밋으로 대체해 `git push --force-with-lease`

**결정 기록**
- **판별 2단계는 수동 등록 게임 중에서만 찾는다**
  모든 게임 중에서 찾으면 Steam 게임끼리 정규화 제목이 같을 때 여러 행이 나와 어느 것을 쓸지 정할 수 없다. 범위를 부분 UNIQUE와 같게 두면 결과가 많아야 한 행이라 "찾기"와 "막기"가 같은 말을 한다. 수동 게임과 Steam 게임을 잇는 것은 M8 병합 문제로 미룸. v1.0에는 Steam 게임이 없어 동작 차이는 없음
- **충돌 시 전체 rollback이 아니라 SAVEPOINT**
  회원가입은 트랜잭션 안에 사용자 INSERT 하나뿐이라 전체 rollback이 괜찮았다. `find_or_create_game`은 게임 등록 API처럼 다른 작업 중간에 불리므로, 전체를 되돌리면 호출한 쪽의 앞선 작업까지 사라진다. SAVEPOINT는 그 지점까지만 되돌린다
- **서비스는 commit하지 않는다**
  게임과 보유 기록(entry)은 함께 저장되거나 함께 취소돼야 한다. 계산(commit)은 호출한 쪽이 한 번에 한다
- **wip 커밋을 force push로 대체** (09-21 오전의 "wip 유지" 결정과 반대)
  이번 wip에는 ERD와 서비스 코드가 섞여 있어, 그 위에 이어서 커밋하면 "문서와 코드 커밋 분리" 규칙을 지킬 수 없었다. wip를 가진 기기가 노트북 하나로 특정되고 처리 방법(`fetch` + `reset --hard`)도 정해져 있어 이력 재작성을 택함. wip 위에 이어서 커밋하는 방법도 검토했다. 09-21 오전 wip는 내용이 한 성격이고 이미 검증까지 끝나 유지할 이유가 있었다는 점이 이번과 다르다

**막혔던 점 / 트러블슈팅**
- 증상: asyncio REPL에 `async with ... as db:` 블록을 입력하자 `expected an indented block`, 이어지는 줄은 전부 `unexpected indent`
  - 원인: `:` 뒤에 `...` 연속 프롬프트가 뜨지 않고 빈 블록으로 처리됨. 여러 줄을 붙여넣을 때 줄바꿈이 끊겨 들어간 것으로 추정
  - 해결: 블록을 쓰지 않는 형태로 변경 — 세션을 `db = AsyncSessionLocal()`로 열고 `await db.close()`로 직접 닫음, 테스트용 함수는 `;`로 이은 한 줄 def
  - 교훈: REPL은 한 줄 문장으로 검증한다. 한 줄 def는 REPL 전용이고 코드 파일에는 쓰지 않는다
- 증상: 데스크톱 B에서 커밋 직전 상태바가 `1↓`, `services/` 파일이 `↓A, U`로 표시
  - 원인: `git reset HEAD~1`은 **이 PC의 책갈피만** 옮긴다. 이미 push된 wip는 원격에 그대로 남아, 새로 커밋하면 이력이 갈라지고 push가 거절되는 상태였음
  - 해결: `git show --stat origin/m1-backend`로 wip 내용 확인 → 로컬에서 두 커밋 작성 → `git push --force-with-lease`
  - 교훈: push한 커밋은 로컬 reset으로 사라지지 않는다. 커밋 전에 상태바 `↓ ↑`와 `git status`의 "behind / diverged"를 먼저 본다. 09-20 데스크톱 A의 "`reset --soft`가 staged 상태를 되돌려 놓음"에 이은 두 번째 reset 사고

**배운 것**
- `git reset` 세 단계 — `--soft`는 책갈피만, `--mixed`(기본값)는 책갈피 + staged 해제, `--hard`는 파일 내용까지 되돌린다. `--hard`만 되돌릴 수 없다
- `--force-with-lease`는 "원격이 내가 마지막으로 fetch한 상태일 때만" 덮어쓴다. push 직전에 fetch하면 기준이 갱신돼 보호가 사라진다
- `SELECT` 조건에서 NULL은 `== None`이 아니라 `.is_(None)`(SQL `IS NULL`)로 비교한다. SQL에서 `= NULL`은 참이 되지 않는다 (09-19의 "NULL과의 비교는 UNKNOWN"과 같은 원리)

**다음에 할 일**
- 노트북 — `git status`가 깨끗한지 확인 → `git fetch origin` → `git reset --hard origin/m1-backend` (**pull 금지**. 갈라진 이력이 merge되며 wip가 되살아남)
- 데스크톱 A — `git pull` → `alembic upgrade head` (`1e1d15e51ba2`까지)
- 게임 등록 API — `GameCreate` schema(`normalize_title`로 422) → router → `find_or_create_game` + entry 생성 → commit. `user_id` 필수 시그니처
- 테스트 — 동시 등록 시 4단계(재조회)를 반드시 타는 pytest
- `06_api_spec.md` — 422 응답의 `Value error, ` 접두사 처리 포함

---

## 2026-09-21(저녁~밤/노트북) — M1 진행 중: 수동 등록 게임 제목에 부분 UNIQUE 추가

**관련 마일스톤**: M1 (백엔드 기초) → 진행 중

**한 일**
- 노트북 동기화 — `git pull` → `docker compose up -d` → `alembic upgrade head` (`43b0fb42aaa8`). 장르 id는 1~8로 들어감 (데스크톱 A는 9~16)
- ERD v1.3 — `games`에 부분 UNIQUE `(title_norm) WHERE steam_appid IS NULL`, 판별 4단계(충돌 시 재조회), 4장 인덱스 표. **코드보다 먼저** 고침
- `app/models/game.py` — `Game.__table_args__`에 `Index("uq_games_title_norm_manual", ..., unique=True, postgresql_where=text(...))`
- 마이그레이션 `1e1d15e51ba2` — `--autogenerate` → `upgrade 43b0fb42aaa8:head --sql`로 `CREATE UNIQUE INDEX ... WHERE steam_appid IS NULL` 확인 → 적용
- HeidiSQL 검증 4건
  - 수동 게임 등록 → 통과
  - 같은 `title_norm`의 수동 게임 → `duplicate key value violates unique constraint "uq_games_title_norm_manual"`
  - 같은 `title_norm`의 Steam 게임(`367520`) → 통과 (부분 UNIQUE 밖)
  - 조회 결과 2행 (id 1 · 3) → 삭제

**결정 기록**
- **`title_norm`에 부분 UNIQUE를 건다** (결정 ④)
  찾아보고(SELECT) 없으면 만드는(INSERT) 사이에 같은 제목 요청이 끼어들면 두 행이 생긴다. 회원가입의 `email` UNIQUE와 같은 틈이다. `games`는 모든 사용자가 공유하는 테이블이라 한 번 꼬이면 정리가 어렵고, 원칙상 동시 실행 상황을 pytest로 검증해야 하므로 판정 기준(DB 제약)이 필요했다. Steam 게임을 빼는 이유와 복합 UNIQUE로 안 되는 이유는 ERD 2.4절
- **이 제약은 새로 합치는 게임을 만들지 않는다**
  UNIQUE가 없어도 판별 2단계가 같은 `title_norm`을 재사용한다. 로직이 이미 하는 일을 동시 요청에서도 DB가 지키게 할 뿐이라, 다른 게임을 합치는 실수(B)는 늘지 않는다
- **기존 일반 인덱스(`index=True`)는 유지**
  부분 인덱스는 수동 게임 행만 담는다. Steam 게임까지 포함한 제목 조회에는 일반 인덱스가 필요하다

**막혔던 점 / 트러블슈팅**
- 증상: `alembic revision --autogenerate`가 `ArgumentError: __table_args__ value must be a tuple, dict, or None`
  - 원인: `Index(...)` 뒤 쉼표 누락. `(A)`는 괄호 친 A일 뿐이고 `(A,)`여야 튜플이다
  - 해결: 쉼표 추가
  - 교훈: 09-20에 두 번 겪은 쉼표 누락과 같은 계열. 트레이스백은 맨 아래 한 줄(무엇이) + **내 파일이 마지막으로 나온 줄**(어디서)만 읽으면 된다
- 증상: (실행 전 검수에서 발견) `text("steam_appid_ IS NULL")` 컬럼명 오타
  - 원인: `text()` 안의 문자열은 SQLAlchemy도 Alembic도 검사하지 않는다. autogenerate는 성공하고 `upgrade` 순간에야 DB가 `column does not exist`로 거부한다
  - 해결: 오타 수정 후 `--sql` 출력에서 최종 SQL을 눈으로 확인
  - 교훈: 문자열로 넘기는 SQL 조각은 **`--sql` 미리 보기가 유일한 검사 단계**다
- 증상: 노트북에서 첫 `docker compose up -d`가 `dockerDesktopLinuxEngine` 파이프 에러
  - 원인: Docker Desktop이 아직 완전히 뜨기 전에 명령을 실행
  - 해결: 잠시 후 재시도로 정상
  - 교훈: 09-21 오전 데스크톱 B와 같은 에러. 이번엔 메시지를 바로 알아봄

**배운 것**
- PostgreSQL은 UNIQUE **제약**에 WHERE를 붙일 수 없어 부분 UNIQUE는 **인덱스**로 만든다. 그래도 위반 메시지는 "unique constraint"로 나오고, 파이썬에서는 같은 `IntegrityError`로 올라온다. `DETAIL`에 부딪힌 값까지 찍힌다
- autogenerate 결과의 `op.f()`는 "naming convention이 지은 최종 이름이니 다시 규칙을 적용하지 마라"는 표시다. 이름을 직접 지으면 붙지 않는다 (장르 UNIQUE에는 붙고 이번 인덱스에는 안 붙은 이유)
- 실패한 INSERT도 SERIAL 번호를 쓴다. 검증에서 id가 1 · 3으로 나와, 거부된 두 번째 INSERT가 2를 가져간 것을 확인

**다음에 할 일**
- `services`의 `find_or_create_game` — ERD 판별 4단계를 코드로. 4단계(충돌 → 재조회)에서 rollback 범위를 정해야 함

---

## 2026-09-21(오후~저녁/데스크톱 A) — M1 진행 중: 장르 결정 · 시드, 정규화 규칙 통합

**관련 마일스톤**: M1 (백엔드 기초) → 진행 중

**한 일**
- 장르 데이터 출처 결정 (`REQUIREMENTS` 10장 미결정 사항 해소) — `REQUIREMENTS` v1.7, ERD v1.1, UI_DESIGN v1.1(목업 장르 `RPG · 오픈월드` → `RPG`, `로그라이크` → `액션`)
- `README` 개발 환경을 기기 3대 기준으로 갱신 (데스크톱 A · B, 노트북)
- `alembic.ini`에 `file_template` 추가 (`날짜_시각_설명`), 기존 마이그레이션 파일을 `git mv`로 이름 변경
- 마이그레이션 `bfea2aef6bcb` — `genres.steam_genre_id` `varchar(10)` UNIQUE NOT NULL
- 마이그레이션 `43b0fb42aaa8` — 장르 8개 시드 (`op.bulk_insert`, downgrade는 `steam_genre_id`로 삭제). `downgrade -1` → `upgrade head` 왕복 확인
- 제목 정규화 규칙 구체화 — ERD v1.2(4단계 · 예시 · 한계), ARCHITECTURE v1.4(규칙은 `core`, 게임 입구는 하나), `REQUIREMENTS` v1.8(F-30 비슷한 게임 후보 · F-31 목록 검색 등록)
- `app/core/normalize.py` 신설 — `normalize_title`(NFKC → casefold → 글자 · 숫자만 → 빈 값 · 길이 검사), `normalize_email`(strip · lower)
- `schemas/user.py`가 `core`의 `normalize_email`을 사용, `LoginRequest`에 같은 validator 추가, `routers/auth.py`의 중복 정규화 줄 제거 → 09-20의 "이메일 정규화 두 곳 중복" 해소
- 검증
  - REPL — ERD 예시 3건 일치, `!!!` 거부, `"ﷺ" * 13`(195자) 통과 · `"ﷺ" * 14`(210자) 거부
  - Swagger — 대문자 + 앞뒤 공백 이메일 로그인 200, `abc` 로그인 401(422 아님)

**결정 기록**
- **장르는 Steam 공식 장르 8개 고정 목록**
  사용자가 장르를 직접 입력하면 `RPG` / `rpg` / `롤플레잉`이 따로 쌓여 장르별 통계(F-11)가 조용히 틀린다. Steam 장르를 따르면 M8 동기화 때 ID로 자동 연결할 수 있다. `인디` · `무료 플레이` · `대규모 멀티플레이어`는 제작 규모 · 가격 · 플레이 방식이라 다른 장르와 전부 겹쳐 제외. 오픈월드 · AAA를 따로 넣어 9~10개로 가는 안도 검토했으나, Steam에서 이들은 장르가 아니라 태그이고 칸이 늘면 장르당 게임 수가 줄어 완주율이 게임 하나에 크게 흔들려 8개로 확정. 목록 상세는 ERD 2.5절
- **`steam_genre_id`는 NOT NULL**
  "장르는 Steam 장르에서만 온다"는 규칙을 코드가 아니라 DB가 강제한다
- **구조 변경과 장르 데이터를 마이그레이션 2개로 분리**
  컬럼 추가(구조)와 목록 입력(데이터)은 되돌릴 이유가 다르다. 시드 마이그레이션은 모델 클래스 대신 `sa.table`로 필요한 컬럼만 적어, 나중에 모델이 바뀌어도 옛 마이그레이션이 깨지지 않게 함
- **마이그레이션 파일명만 바꾸고 revision ID는 유지**
  revision ID는 각 DB의 `alembic_version`에 저장돼 있어, 바꾸면 PC 3대의 DB를 전부 손으로 고쳐야 한다. 파일명은 Alembic이 읽지 않으므로 자유롭게 바꿀 수 있다
- **뜻이 같은 표기(`7` / `VII`)는 정규화 규칙으로 잡지 않는다**
  로마 숫자 변환 규칙을 넣으면 `Mega Man X`가 `Mega Man 10`과 합쳐진다. 중복 행(실수 A)은 나중에 합칠 수 있지만, 다른 게임을 합친 것(실수 B)은 공유 테이블 전체를 오염시킨다. 규칙은 A 쪽으로 기울이고, 뜻 수준은 별칭 · F-30으로 보완
- **서버 에러 메시지는 평서체, 이모티콘 없음**
  다른 API 메시지와 말투를 맞춘다. 친근한 문구가 필요하면 화면(M3)에서 정한다

**막혔던 점 / 트러블슈팅**
- 증상: `git mv`가 `No such file or directory`, 메시지에는 **원본** 경로가 찍힘
  - 원인: 실제 문제는 **목적지** 경로 오타 (`alemblc`, `2026919`)
  - 해결: 목적지를 `alembic/versions/20260919_1708_create_v1_0_tables.py`로 수정
  - 교훈: 에러에 찍힌 경로가 곧 틀린 경로라는 법은 없다. 인자가 둘인 명령은 둘 다 확인한다
- 증상: HeidiSQL에서 장르 조회 결과가 빈 화면인데 에러도 없음
  - 원인: `SELECT FROM genres`로 `*`가 빠짐. PostgreSQL은 컬럼이 0개인 SELECT도 문법상 허용해 "0열짜리 행 8개"를 돌려줌
  - 해결: `SELECT * FROM genres ORDER BY id`
  - 교훈: 09-19의 `path` 오타와 같은 유형 — 빠뜨린 것이 에러가 아니라 "없는 것"으로 조용히 처리된다
- 증상: HeidiSQL 테이블 구조 탭의 NULL 체크 표시가 기대와 달라 NOT NULL이 안 걸린 것처럼 보임
  - 해결: CREATE 코드 탭에서 `NOT NULL`을 직접 확인
  - 교훈: 도구의 요약 화면보다 DB가 실제로 실행한 DDL이 기준이다
- 증상: 길이 제한을 초과 하는 경우를 만들어 길이 초과 검증 ─ 정상 통과함 (`12 * "ﷺ"`)
  - 원인: 코드가 아니라 **검증 예시**가 틀림. 한 글자가 걸러진 뒤 15자라 12개면 180자로 200 이내
  - 해결: 경계를 계산해 13(195자, 통과) · 14(210자, 거부)로 재검증
  - 교훈: 경계값 테스트는 경계 양쪽을 계산해서 고른다

**배운 것**
- SERIAL은 번호를 재사용하지 않는다. `downgrade` → `upgrade`를 한 데스크톱 A는 장르 id가 9~16, 노트북은 1~8이다. **코드에서 장르를 id 숫자로 가리키면 안 되고** `steam_genre_id`나 `name`으로 찾아야 한다
- NFKC는 글자 수를 늘릴 수 있다 (`ﷺ` 1자 → 18자). 길이 검사를 원본이 아니라 정규화 결과에 해야 하는 이유
- validator 안의 `ValueError`는 Pydantic이 422로 바꾸면서 메시지 앞에 `Value error, `를 붙인다. 쓴 글자와 나가는 글자가 다르다
- `normalize.py`는 FastAPI를 모른다. `HTTPException`이 아니라 `ValueError`를 던져야 `core`가 HTTP에 의존하지 않는다

**발견 사항 (지금 조치하지 않음)**
- 09-19 결정에서 `game_genres`를 Core `Table`로 둔 근거로 "M8 작업 목록에 장르 동기화가 없다"고 적었는데, `steam_genre_id`는 바로 M8 장르 자동 연결을 위한 것이다. 연결 자체에 속성이 생기는 건 아니라 `Table` 유지에는 문제가 없지만, MILESTONES M8에 "Steam 장르 자동 연결 (`steam_genre_id` 기준)" 항목 추가가 필요하다

**다음에 할 일**
- 결정 ④ — `title_norm` 부분 UNIQUE 여부 (ERD 수정 + 마이그레이션 동반)
- `services`의 게임 중복 판별
- 작업 기기를 데스크톱 A → 노트북으로 이동 (`git pull` → `alembic upgrade head`)

---

## 2026-09-21(오전~점심/데스크톱 B) — M1 진행 중: 인증 파트 완료 (재발급 재검증 · 로그아웃 · get_current_user), 게임 CRUD · 테스트 남음

**관련 마일스톤**: M1 (백엔드 기초) → 진행 중

**한 일**
- 데스크톱 B에 저장소 클론 후 환경 구성 — venv · `server/.env` · 루트 `.env` 작성, Docker Desktop 실행, `alembic upgrade head`(`0a6ba7b72cfb` 적용)
- HeidiSQL 12.14 → 12.21 재설치 (PostgreSQL 접속 라이브러리 로드 실패)
- 토큰 재발급 실패 경로 재검증 (09-20 밤 `wip` 커밋 `605b62a`의 미완료분)
  - 로그인 2회로 유효 토큰 2개 생성 → refresh 1회 → 폐기된 토큰을 쿠키에 되돌려 심고 refresh
  - 401 `다시 로그인해 주세요` + **3행 전부 폐기**. 따로 로그인해 떠돌던 1번 행까지 같은 시각으로 폐기됐고, 먼저 rotation된 2번 행은 원래 폐기 시각 유지
  - 다음 요청이 401 `인증 정보가 없습니다`로 **메시지가 바뀜** → 실패 응답에서 쿠키가 삭제된 것 확인
- `POST /api/auth/logout` 구현 및 검증
  - 204, 네트워크 탭 응답 헤더에서 삭제용 `Set-Cookie`(빈 값 · `Max-Age=0` · `Path=/api/auth`) 확인
  - 해당 토큰 행만 폐기, 쿠키 없는 상태로 한 번 더 호출 → 다시 204
  - 로그아웃 후 refresh → 401 `인증 정보가 없습니다`
- `app/deps.py` — `get_current_user` 의존성 (`HTTPBearer(auto_error=False)`, 토큰 검증 후 DB에서 사용자 재확인)
- `GET /api/auth/me` 추가 *(계획에 없던 작업)* — `get_current_user` 동작 확인 수단이자 M2 계정 정보 화면용
  - Swagger Authorize 후 200, 응답에 `password_hash` 없음
  - 토큰 없음 → 401, 서명 끝 한 글자 변조 → 401 (둘 다 `인증이 필요합니다`, `www-authenticate: Bearer` 헤더 포함)
- 코드 정리 — 줄 끝 · 빈 줄 공백 제거(편집기 Trim Trailing Whitespace 적용), 오타, 사실과 달라진 주석("추후 logout에서 사용할 예정") 삭제
- 커밋을 정리 / 로그아웃 / `get_current_user` 3개로 분리 (GitHub Desktop 줄 단위 선택)

**결정 기록**
- **로그아웃은 실패 경로 없이 항상 204 (멱등)**
  로그아웃의 목적은 "로그아웃된 상태"이지 "토큰 찾기"가 아니다. 쿠키가 없든 이미 폐기된 토큰이든 끝난 뒤의 상태는 같으므로 에러를 낼 이유가 없다. 401을 주면 화면은 "로그아웃 실패"를 어떻게 처리해야 할지 애매해진다
- **로그아웃에 access 토큰을 요구하지 않음**
  `get_current_user`를 붙이면 access 토큰이 만료된 사용자는 로그아웃을 못 한다. 필요한 정보(refresh 토큰)는 쿠키에 다 있다
- **로그아웃은 현재 기기의 토큰만 폐기**
  로그인은 기존 토큰을 폐기하지 않아 기기마다 토큰이 공존한다. 들고 온 토큰만 폐기하는 것이 일반적인 동작이며, "모든 기기에서 로그아웃"은 별도 기능이라 구현하지 않고 `REQUIREMENTS` 4.4절(F-29)로 이관
- **`OAuth2PasswordBearer`가 아닌 `HTTPBearer`**
  FastAPI 공식 튜토리얼은 `OAuth2PasswordBearer`를 쓰지만, 이는 로그인이 form-data(`username` + `password`)로 들어온다고 가정한다. 이 프로젝트의 로그인은 JSON 본문이라 구조가 맞지 않는다. argon2 결정 때의 "튜토리얼이 passlib 기준"과 같은 상황 — 문서가 가정하는 구조가 내 구조와 같은지부터 확인한다
- **`get_current_user`는 `raise`로 실패를 처리**
  09-20 밤의 쿠키 삭제 버그는 "인자로 받은 응답 객체에 쿠키를 얹었는데 `raise`로 빠져나가서" 생겼다. 여기서는 얹을 쿠키가 없고, 필요한 헤더(`WWW-Authenticate`)는 `HTTPException`에 직접 담았으므로 예외 처리기가 만드는 새 응답에 함께 실린다. `raise`가 문제가 아니라 **무엇을 어느 객체에 담았는지**가 핵심
- **`wip` 커밋을 `feat`으로 재작성하지 않고 유지** (09-20 밤 결정 변경)
  이미 push된 커밋이라 메시지만 바꿔도 force push가 필요하다. 여러 기기에서 같은 브랜치를 쓰는 상황에서 이력을 재작성하면, 옛 이력을 가진 기기에서 pull할 때 이력이 갈라진다. 또 커밋 내용은 오늘 재검증을 통과했고, 메시지의 "재검증 미완료"도 그 시점엔 사실이었다. 이력을 고치는 대신 이 기록으로 "검증 완료"를 이어 붙인다
- **공백 · 오타 정리를 기능 커밋과 분리**
  편집기가 저장하며 파일 전체의 공백을 지워, 기능과 무관한 변경 13줄이 생겼다. 섞으면 기능 커밋 diff에서 진짜 변경을 찾기 어렵다. 분리한 결과 정리 커밋은 +13/−13(내용 불변), 로그아웃 커밋은 +33/−0(순수 추가)으로 수치만 봐도 성격이 드러난다

**막혔던 점 / 트러블슈팅**
- 증상: `docker compose up -d`에서 `failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine`. 리눅스가 없다는 뜻으로 읽고 `wsl --install`을 실행했더니 "이미 있음"
  - 원인: 파이프 이름에 `Linux`가 들어 있을 뿐, 메시지 본문은 "경로가 맞는지, 데몬이 실행 중인지 확인하라"였다. 이 파이프는 Docker Desktop이 **켜질 때** 만들어지는데, 설치만 되고 실행이 안 된 상태였음
  - 해결: Docker Desktop 실행 후 재시도
  - 교훈: M0의 `Could not import module` 건과 같다. 에러 메시지 속 **단어**가 아니라 **문장**을 읽을 것
- 증상: `server/.env`의 첫 줄이 `DATABASE_URL=DATABASE_URL=postgresql+asyncpg://...`
  - 원인: `.env.example`에서 키 이름까지 함께 복사해 붙여넣음. 첫 `=` 뒤 전체가 값이 되어 드라이버를 찾을 수 없는 문자열이 됨
  - 해결: 중복된 키 이름 삭제. 이후 `alembic upgrade head` 성공으로 접속 정보가 맞음을 확인
  - 교훈: `.env.example`은 **키 이름이 이미 적혀 있는 틀**이다. 값만 채운다
- 증상: JWT 서명 키가 화면에 두 번 노출됨 — `.env`를 열어둔 채 찍은 스크린샷, 키 생성 명령의 터미널 출력
  - 원인: 비밀값을 "커밋"만 조심하면 된다고 생각함. 실제로는 키를 **만드는 순간**과 **붙여넣는 순간** 모두 화면에 뜬다
  - 해결: 두 번 모두 키를 새로 발급. 두 번째부터는 `python -c "import secrets; print(secrets.token_urlsafe(32))" | Set-Clipboard`로 화면을 거치지 않고 클립보드로 보냄
  - 교훈: M0의 `print(settings.database_url)` 건의 확장판. 비밀값은 화면에 띄우는 순간 전부가 노출 경로다. `.env`를 열어둔 창은 캡처하지 않는다
- 증상: HeidiSQL 접속 시 `libpq-17.dll을 불러올 수 없습니다 (오류 126)`. `libpq-15`로 바꿔도 동일
  - 원인: 오류 126은 "모듈을 찾을 수 없음"인데, 드롭다운에 파일이 보였으므로 DLL 자체가 아니라 **그것이 의존하는 다른 부품**이 없던 것으로 판단
  - 해결: HeidiSQL 삭제 후 12.21로 재설치
  - 교훈: 클라이언트 도구가 안 붙어도 DB가 죽은 건 아니다. `alembic upgrade head` 성공이 이미 "컨테이너 · 접속 정보 · 포트 정상"의 증거였고, HeidiSQL 없이도 `docker compose exec db psql`로 확인할 수 있다
  - 후속 확인: 데스크톱 A · 노트북은 12.21 이전 버전으로도 정상 접속된다. 원인은 버전이 아니라 데스크톱 B의 설치 상태였던 것으로 추정하며, 재설치로 해결된 것이 이를 뒷받침한다
- 증상: 로그인 200인데 DevTools 애플리케이션 탭 쿠키 목록이 비어 있음
  - 원인: 처음엔 쿠키 `Path=/api/auth`와 현재 페이지(`/docs`)가 달라 목록에서 빠진 것으로 판단했으나, **같은 `/docs` 페이지에서 다른 탭을 눌렀다 돌아오자 쿠키가 나타나** 이 가설은 반증됨. 실제로는 애플리케이션 탭 목록이 자동 갱신되지 않은 것
  - 해결: 네트워크 탭에서 응답의 `Set-Cookie`와 **다음 요청의 `Cookie` 헤더**로 저장 · 재전송을 확인. 요청에 `Cookie`가 실려 있다는 것 자체가 저장됐다는 증거
  - 교훈: 판단 근거는 항상 네트워크 탭의 실제 헤더. 09-19의 "반증이 나오면 가설을 버린다"를 다시 확인

**배운 것**
- 쿠키에는 "삭제" 명령이 없다. 빈 값 · 지금 만료 · `Max-Age=0`인 쿠키로 **덮어써서** 지운다. 그래서 삭제할 때도 이름 · 경로가 심을 때와 같아야 한다 (다르면 다른 쿠키를 덮어쓴다)
- 09-20 밤의 "Swagger로는 쿠키를 검증할 수 없다"를 정정 — 정확히는 **`Set-Cookie`만** 안 보인다. 같은 Swagger 화면에 `www-authenticate`는 표시됐다. `Set-Cookie`는 브라우저가 JS에게 숨기도록 정해진 금지 헤더이고, 나머지 헤더는 그런 제한이 없다
- 결과로 원인을 판정할 수 있다. 재사용 감지 응답의 `Set-Cookie`는 못 봤지만, 다음 요청 메시지가 `인증 정보가 없습니다`로 바뀐 것은 코드상 쿠키가 안 실렸을 때만 가능하다. 실패 메시지를 두 종류로 나눠둔 결정이 검증 수단이 됐다
- 로그인은 새 토큰을 추가할 뿐 기존 토큰을 폐기하지 않는다. 테스트 중 로그인을 두 번 하자 유효 토큰이 2개 생겼고, 재사용 감지가 둘 다 폐기하는 것으로 "해당 사용자의 살아 있는 토큰 전부"가 실제로 작동함을 확인
- access 토큰 노출과 서명 키 노출은 무게가 다르다. 키가 새면 누구나 토큰을 **만들 수 있고**(영구), access 토큰이 새면 그 토큰 **하나를 15분간** 쓸 수 있다. access 토큰 수명을 짧게 둔 이유(ARCHITECTURE 4.1절)가 이것
- 주석도 코드와 함께 늙는다. 09-20 밤 커밋의 `(추후 logout에서 사용할 예정)`은 그때는 사실이었고, logout을 만든 순간 거짓말이 됐다. 문서의 "한 곳만 고치면 나머지가 거짓말로 남는다"가 주석에도 적용된다

**발견 사항 (지금 조치하지 않음)** — M5 `README` 실행 방법 · 클린룸 검증 재료
- Docker Desktop은 설치가 아니라 **실행 중**이어야 한다
- HeidiSQL이 libpq 로드 오류(126)를 내면 재설치한다. 특정 버전이 필요한 것은 아니다 (이전 버전도 다른 PC에서 정상)
- `.env`는 `.env.example`을 복사하되 **값만** 채운다
- `JWT_SECRET_KEY`는 기기마다 새로 발급한다 (공유하지 않음). 생성 시 `| Set-Clipboard`로 화면 노출을 피한다
- 클론 직후 DB는 비어 있으므로 `alembic upgrade head` → 가입부터 다시

**다음에 할 일**
- 장르 시드 (게임 CRUD 착수 전)
- 제목 정규화 함수(`title_norm`) + 이메일 정규화 통합 — 같은 규칙이 `schemas/user.py`와 `routers/auth.py` 두 곳에 있는 문제
- 게임 중복 판별(`services`) → 보유 기록 CRUD (`user_id` 필수 시그니처)
- `06_api_spec.md` — 인증 흐름이 끝났으니 에러 응답 규칙(401 메시지 3종 · 409 · 422)을 정리하기 좋은 시점
- 다른 기기로 옮길 땐 `git pull`부터. 이력을 재작성하지 않았으므로 노트북 · 데스크톱 A 모두 평소대로 pull하면 됨

---

## 2026-09-20(밤/노트북) — M1 진행 중: 토큰 재발급(rotation) 및 재사용 감지 구현

**관련 마일스톤**: M1 (백엔드 기초) → 진행 중

**한 일**
- ARCHITECTURE v1.3 개정 — 4.1절에 재사용 감지 단락 추가. ERD 2.2절이 `revoked_at`을 남기는 목적으로 이미 명시하고 있었으나 인증 흐름엔 없었음. **코드보다 먼저** 고침
- `app/routers/auth.py`
  - `REFRESH_COOKIE_PATH` 상수 추가
  - `set_refresh_cookie` / `clear_refresh_cookie` 헬퍼 분리, `login`도 헬퍼를 쓰도록 변경
  - `POST /api/auth/refresh` — 조회 · 유효성 확인 · 폐기를 `UPDATE ... RETURNING` 한 문장으로 처리한 뒤 새 토큰 한 쌍 발급
  - 폐기된 토큰이 다시 들어오면 해당 사용자의 살아 있는 토큰을 전부 폐기하고 401
- 검증 (Swagger + DevTools + HeidiSQL)
  - 로그인 → refresh 3회, `refresh_tokens` 1행 → 4행. **살아 있는 행은 항상 정확히 1개**
  - 브라우저 쿠키의 Expires가 DB `expires_at`과 같은 시각 → 쿠키가 매번 새로 심긴 것 확인
  - 폐기된 토큰을 쿠키에 되돌려 심고 요청 → 401 + 4행 전부 폐기
  - 이미 폐기된 행의 `revoked_at`이 덮어써지지 않음
- 실패 경로에서 쿠키가 삭제되지 않는 문제를 발견해 수정 (아래 트러블슈팅) — **재검증은 다음 세션**

**결정 기록**
- **조회 · 유효성 확인 · 폐기를 `UPDATE` 한 문장으로**
  `SELECT`로 찾고 파이썬에서 검사한 뒤 `UPDATE`하면 그 사이에 틈이 생긴다. 같은 토큰으로 두 요청이 동시에 들어오면 둘 다 "유효함"을 보고 통과해, 탈취자와 사용자가 거의 동시에 재발급을 시도하는 바로 그 상황에서 감지 장치가 무력화된다. `UPDATE`는 DB가 쪼개지 않고 실행하므로 한쪽만 1행을 바꾸고 다른 쪽은 0행이 된다
- **일괄 폐기에 `revoked_at IS NULL` 조건을 넣음**
  없으면 이미 폐기된 행의 폐기 시각까지 감지 시점으로 덮어써져, "언제 rotation됐는지" 이력이 한 시각으로 뭉개진다. 실제로 검증 후 1~3번 행의 원래 폐기 시각이 그대로 남은 것을 확인
- **재발급 실패 사유를 두 메시지로 나눔**
  "쿠키 없음"은 `인증 정보가 없습니다`, "폐기 · 만료 · 존재하지 않는 토큰"은 전부 `다시 로그인해 주세요`로 통일. 후자를 세분하면 공격자에게 토큰 상태를 알려주게 되지만, 전자는 요청자가 이미 아는 사실(쿠키를 안 보냈다)이라 노출이 아니다. 실제로 이 구분 덕에 쿠키 삭제 버그를 응답 메시지만으로 특정할 수 있었다
- **실패 경로에서도 `commit`을 호출**
  재사용 감지의 일괄 폐기는 "쓰기"다. `commit` 없이 응답을 반환하면 `get_db`가 세션을 반납하며 롤백돼 폐기가 없던 일이 된다
- **커밋 type으로 규칙에 없는 `wip`을 사용**
  구현은 끝났고 실행도 되지만 검증이 남은 상태다. `feat`으로 적으면 나중에 이력에서 "검증된 기능"과 구분되지 않는다. 기기를 옮겨 이어서 작업하는 상황이라 그 구분이 필요했음. PR 전에 `feat(M1):`으로 정리한다

**막혔던 점 / 트러블슈팅**
- 증상: 재사용 감지로 401은 정상적으로 나오는데, 그 응답에서 쿠키가 삭제되지 않음. 다음 요청의 메시지가 `인증 정보가 없습니다`가 아니라 `다시 로그인해 주세요`로 나와서 발견
  - 원인: FastAPI가 인자로 넘겨주는 `response`는 실제 응답이 아니라 "헤더를 적어두는 메모지"다. 함수가 `return`으로 끝나면 FastAPI가 그 내용을 진짜 응답에 옮겨 붙이지만, `raise HTTPException`으로 빠져나가면 **예외 처리기가 응답을 처음부터 새로 만든다.** `clear_refresh_cookie`는 실행됐지만 그 결과가 실린 메모지가 버려진 것
  - 해결: 실패 응답을 `JSONResponse`로 직접 만들고 거기에 쿠키 삭제를 얹어 `return`. 쿠키가 아예 없는 첫 번째 401은 지울 것도 없으므로 `HTTPException` 유지
  - 교훈: **`raise` 경로와 `return` 경로는 서로 다른 응답 객체를 쓴다.** 응답에 무언가를 얹는 코드(쿠키 · 헤더)가 실패 경로에 있으면 실행은 되는데 밖으로 나가지 않는다. `login`이 멀쩡했던 건 정상 종료 경로에서만 쿠키를 심었기 때문. M1의 "들여쓰기로 클래스 밖에 새어 나간 메서드"와 같은 계열 — 문법도 실행도 정상인데 의도만 어긋난다

**배운 것**
- `Set-Cookie`는 브라우저가 JS에게 보여주지 않는 헤더다. HttpOnly 쿠키를 만들어두고 JS가 헤더로 읽으면 의미가 없기 때문. Swagger도 JS로 동작하므로 **Swagger 화면의 Response headers로는 쿠키 관련 동작을 검증할 수 없다.** 성공한 200 응답에도 `set-cookie`가 안 보였다. DevTools 네트워크 탭에서 봐야 한다 — 검증 수단이 애초에 그 값을 못 보여주는 함정
- uvicorn 접근 로그에는 상태 코드만 남는다. 실패 사유를 응답 본문으로만 구분하기로 한 대가로, **나 자신도 로그만 보고는 원인을 알 수 없다.** 401이 6줄 찍혀 있어도 어느 것이 어느 경로인지 구분되지 않았다
- 그 로그에 토큰 · 비밀번호가 한 글자도 안 남은 것은 우연이 아니다. 로그인 정보를 쿼리스트링이 아닌 요청 본문으로, refresh 토큰을 쿠키(헤더)로 받은 구조 덕이다. **URL에 넣은 값은 로그에 남는다** — 로그는 백업 · 공유되므로 M0의 `print(settings.database_url)` 건과 같은 계열의 위험이다

**다음에 할 일**
- 데스크톱 B에서 저장소 클론부터. `server/.env`는 Git 추적 대상이 아니므로 직접 생성해야 한다 (`.env.example` 참고, `JWT_SECRET_KEY`는 `secrets.token_urlsafe(32)`로 새로 발급). 루트 `.env`도 마찬가지
- venv 생성 → `pip install -r requirements.txt` → `docker compose up -d` → `alembic upgrade head` → 가입부터 다시
- 클론 후 막힌 지점을 메모 — M5 `README` 실행 방법 작성과 클린룸 검증의 실제 재료가 된다
- 재발급 실패 경로 재검증 — 재사용 감지 401 이후 한 번 더 요청했을 때 메시지가 `인증 정보가 없습니다`로 **바뀌는지**가 합격 신호
- 로그아웃 (refresh 토큰 폐기 + 쿠키 삭제) → `get_current_user` 의존성 → `GET /api/auth/me`
- MILESTONES rotation 체크박스는 재검증 통과 후에 체크

---

## 2026-09-20(오후~저녁/데스크톱 A) — M1 진행 중: JWT 설정 및 로그인 API 구현

**관련 마일스톤**: M1 (백엔드 기초) → 진행 중

**한 일**
- `server/.env`에 `JWT_SECRET_KEY` 추가 (`secrets.token_urlsafe(32)`로 생성), `.env.example`에 키 이름만 반영
- `app/core/config.py` — JWT 서명 키(필수) · 알고리즘 · access/refresh 수명 설정 추가
- `app/core/security.py`
  - `create_access_token` / `decode_access_token` — PyJWT, HS256, `sub`에 사용자 id만
  - `create_refresh_token` — `secrets.token_urlsafe(32)`
  - `hash_refresh_token` — SHA-256 (ERD 2.2절)
- `app/schemas/user.py` — `LoginRequest` / `TokenResponse` 추가
- `app/routers/auth.py` — `POST /api/auth/login`
  - access 토큰은 응답 본문, refresh 토큰은 원문을 쿠키로 · 해시만 DB에
  - 쿠키 `pl_refresh_token` — `httpOnly` · `Secure` · `SameSite=Strict` · `Path=/api/auth`
  - 없는 계정에도 더미 해시로 검증을 돌려 응답 시간을 맞춤
- REPL 검증
  - 토큰 발급 → 복호화로 id 복원, 서명 훼손(`t + "x"`) · 잘못된 문자열은 `None`
  - refresh 토큰: 매번 다른 값, 해시는 64자, 같은 입력이면 항상 같은 해시
- jwt.io에 access 토큰을 붙여넣어 서버 키 없이 payload가 읽히는 것 확인 (`sub`/`iat`/`exp`, 차이 900초)
- Swagger 검증 — 가입 201 → 로그인 200 → 비밀번호 오류 401 → 없는 계정 401(같은 문구)
- DevTools Network — 위 두 401의 응답 시간이 **42ms / 42ms**로 동일
- DevTools Application — 쿠키 속성 확인. 동시에 **v0 Django가 심은 `csrftoken`(만료 2027-08-31)이 아직 살아 있는 것**을 확인
- HeidiSQL — `refresh_tokens` 1행 생성, 쿠키의 원문과 DB의 해시가 서로 다른 값, `expires_at`이 정확히 14일 뒤, `revoked_at`은 NULL

**결정 기록**
- **refresh 토큰은 JWT가 아닌 무작위 문자열**
  JWT의 장점은 "DB를 보지 않고 서명만으로 검증"인데, refresh 토큰은 로그아웃 폐기 · rotation · 탈취 감지(ARCHITECTURE 4.1절)를 위해 어차피 매번 DB를 조회해야 한다. 그 순간 JWT의 이점이 사라지고 만료 로직 · 서명 키 관리만 늘어난다. 게다가 JWT는 payload를 누구나 읽을 수 있지만(jwt.io에서 확인), 무작위 문자열은 DB 없이는 아무 의미가 없어 더 안전하다
- **refresh 토큰 해시는 argon2가 아닌 SHA-256**
  argon2가 느린 것은 사람이 만든 약한 비밀번호를 대입하는 공격을 막기 위해서다. 이 토큰은 서버가 만든 32바이트 무작위값이라 대입이라는 개념이 성립하지 않으므로 느릴 이유가 없다. 또 SHA-256은 salt가 없어 같은 입력이면 항상 같은 해시가 나오고, 덕분에 들어온 토큰을 해싱해 `WHERE token_hash = ...`로 바로 조회할 수 있다. argon2였다면 salt 때문에 전체 행을 훑어야 한다
- **로그인 응답 시간까지 통일** (09-20 오전 기록의 "로그인 쪽은 막는다" 이행)
  UI_DESIGN 3.1절의 메시지 통일만으로는 부족하다. argon2 검증이 수십 ms라 "계정 있음"과 "없음"의 응답 시간이 갈려, 메시지를 읽지 않고 시간만 재도 계정 존재 여부를 알 수 있다. 계정이 없을 때도 더미 해시로 검증을 한 번 돌려 시간을 맞췄고, 실측 결과 42ms / 42ms로 동일했다

**막혔던 점 / 트러블슈팅**
- 증상: `decode_access_token`에서 `TypeError: 'dict' object is not callable`. `payload("sub")`를 `payload.get("sub")`로 고쳤는데 **같은 에러가 그대로** 재발
  - 원인: 두 번째 에러는 이미 import한 옛 코드가 실행된 결과였다. 파이썬은 import 시점에 모듈을 메모리에 올리고 이후 파일을 다시 읽지 않지만, 트레이스백을 출력할 때는 해당 줄을 파일에서 그때 읽어온다. 그래서 **실행되는 코드(옛 버전)와 화면에 표시되는 줄(수정본)이 어긋났다**
  - 해결: REPL 재시작
  - 교훈: 파일을 고쳤으면 REPL을 껐다 켠다. 서버는 `--reload`가 대신 해주므로 이 함정은 REPL에서만 나타난다. "고쳤는데 그대로"일 때 코드를 더 의심하기 전에 실행 주체가 새 코드를 읽었는지부터 확인할 것
- 증상: `auth.py`에 `"(" was not closed` 에러 2건(116 · 117번 줄). 표시된 줄에는 문제가 없어 한참 찾음
  - 원인: `token_hash=hash_refresh_token(refresh_token)` 끝의 쉼표 누락. **같은 날 오전 `password_hash=...`에서 겪은 것과 동일한 실수**
  - 해결: 쉼표 추가
  - 교훈: 인자가 함수 호출 `)`로 끝나면 괄호가 닫힌 것처럼 보여 쉼표를 빠뜨리기 쉽다. 중첩 괄호에서는 바깥쪽까지 줄줄이 "안 닫힘"으로 표시되므로, **가장 안쪽 괄호부터 그 아래 줄을 훑는다**
- 증상: 커밋을 2개로 나누려 했는데, `git add`로 4개만 지정했음에도 6개 파일이 전부 커밋됨
  - 원인: 앞서 잘못된 메시지를 되돌리려고 실행한 `git reset --soft HEAD~1`이 **커밋에 있던 파일 6개를 staged 상태로 되돌려 놓았다.** `git add`는 스테이징을 교체하는 것이 아니라 추가하는 것이므로, 이미 올라와 있던 6개가 그대로 남아 있었음
  - 해결: `git reset`(옵션 없이)으로 스테이징만 전부 해제한 뒤, 커밋 1의 4개만 add → 커밋 → 나머지 2개 add → 커밋
  - 교훈: **`git commit`은 방금 add한 것이 아니라 "그 시점에 staged인 전부"를 커밋한다.** commit 직전에 `git status`의 `Changes to be committed` 목록을 눈으로 확인할 것. M0의 "원인을 확인하기 전에 `git add .`를 하면 정체 모를 변경이 섞인다"와 같은 유형이다

**배운 것**
- JWT는 암호화가 아니라 서명이다. jwt.io에 토큰을 넣자 서버 키 없이 payload가 그대로 읽혔다. 내용을 숨기는 것이 아니라 "변조되지 않았음"만 보장하므로 payload에는 사용자 id 외에 아무것도 넣지 않는다. 같은 화면에서 `Valid JWT`(모양이 맞음)와 `Invalid Signature`(도장이 안 맞음)가 함께 표시되는데, 서로 다른 것을 말하는 두 판정이다
- `jwt.decode`의 `algorithms`가 리스트인 이유 — 허용 목록을 명시하지 않으면 토큰 헤더에 `"alg": "none"`을 적어 보내 검증을 건너뛰는 공격이 가능하다. 토큰이 자기 검증 방식을 스스로 정하게 두면 안 된다
- M0에서 "지금 조치하지 않음"으로 남겨둔 발견 사항이 실제로 값을 했다. v0 Django의 `csrftoken`이 1년 뒤인 지금도 브라우저에 남아 있어, 쿠키 이름에 `pl_` 접두사를 붙이지 않았다면 다른 프로젝트와 덮어쓸 수 있었다
- `users.id`가 데스크톱 A에서는 5부터 시작했다(노트북은 1). 9/19 밤 제약 검증 때 이 DB에서 INSERT가 여러 번 차단되며 SERIAL 번호를 소모한 탓이다. 같은 코드라도 DB의 이력에 따라 id가 달라진다

**다음에 할 일**
- 토큰 재발급(rotation) — 기존 토큰 `revoked_at` 기록 후 새 토큰 발급, 폐기된 토큰 재사용 시 401
- 로그아웃 (refresh 토큰 폐기 + 쿠키 삭제) → `get_current_user` 의존성
- 이메일 정규화가 `schemas/user.py`와 `routers/auth.py` 두 곳에 중복돼 있음 — 게임 CRUD의 `normalize_title` 작업과 함께 한 곳으로 통합 (MILESTONES에 항목 추가)

---

## 2026-09-20(9/19 저녁 ~ 9/20 오전/노트북) — M1 진행 중: 비밀번호 해싱 결정 및 회원가입 API 구현

**관련 마일스톤**: M1 (백엔드 기초) → 진행 중

**한 일**
- 비밀번호 해싱 라이브러리 결정 (`REQUIREMENTS` 10장 미결정 사항 해소)
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
  "이미 사용 중인 이메일"을 알려주면 제3자가 특정 이메일의 가입 여부를 확인할 수 있다. 막으려면 가입을 항상 성공으로 응답하고 메일로 안내해야 하는데, 이는 SMTP 구성 · 인증 토큰 테이블 · 화면 추가까지 딸려오는 범위 확대라 v1.0에서 제외한다. 대신 **로그인 쪽은 막는다** (다음 세션 구현 예정) — UI_DESIGN 3.1절의 메시지 통일에 더해, 없는 계정에도 더미 해시로 검증을 한 번 돌려 응답 시간을 맞춘다(argon2가 느려 "계정 있음 ≈ 50ms / 없음 ≈ 2ms"로 갈리는 것을 메시지와 무관하게 구분당할 수 있음). 완전 차단은 `REQUIREMENTS` 4.4절 F-27로 이관

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
- `created_at`이 `2026-09-19 23:19:00+00`으로 저장됐다. `timestamptz`라 UTC로 보관되며, 한국 시간 표시는 화면에서 변환한다 (ERD 2.0절)

**다음에 할 일**
- 로그인 — access 토큰(응답 본문) + refresh 쿠키(httpOnly, 프로젝트 접두사), 없는 계정에도 더미 해시 검증
- 토큰 재발급(rotation) → 로그아웃 → `get_current_user` 의존성
- 작업 PC를 노트북 → 데스크톱 A로 이동 (`git pull` 먼저)

---

## 2026-09-19(저녁~밤/데스크톱 A) — M1 진행 중: 모델 6종 정의 및 첫 마이그레이션 적용

**관련 마일스톤**: M1 (백엔드 기초) → 진행 중

**한 일**
- `app/models/base.py` — `DeclarativeBase` 상속 `Base` 선언, 제약조건 작명 규칙(`naming_convention`) 정의
- v1.0 범위 모델 6종 정의 (ERD 2장 기준)
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
  인터넷 예제 다수가 엔진과 `Base`를 한 파일에 두지만, ARCHITECTURE 6장에서 `core/`는 "설정 · DB 연결 · 보안", `models/`는 "테이블 정의"로 나눠 두었음. `Base`는 연결이 아니라 테이블 정의의 공통 조상이므로 `models/` 소속. 의존 방향이 `models/` → `core/` 한쪽으로만 흘러 순환 import를 원천 차단하는 효과도 있음
- **제약조건 작명 규칙(`naming_convention`)을 `Base`에 미리 부여**
  규칙이 없으면 PostgreSQL이 `entries_check` 같은 이름을 자동 부여해, 나중에 특정 제약만 삭제 · 수정할 때 대상을 지목할 수 없음. 실제로 검증 단계에서 에러 메시지에 `ck_entries_rating_range`처럼 이름이 찍혀 5개 CHECK 중 무엇이 걸렸는지 즉시 판별됨
- **`game_genres`를 ORM 클래스가 아닌 Core `Table` 객체로 정의**
  컬럼이 `(game_id, genre_id)` 둘뿐이고 추가할 정보가 없음(ERD 2.5절). 클래스로 만들면 연결 하나마다 빈 객체를 생성하게 됨. 대신 나중에 연결 자체에 속성이 필요해지면 클래스로 전환하는 마이그레이션이 필요하다는 점을 감수함 — M8 작업 목록에 장르 동기화가 없어 당분간 발생하지 않을 것으로 판단
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
- 비밀번호 해싱 라이브러리 결정 (`REQUIREMENTS` 10장) 후 회원가입 API
- 로그인(access 토큰 + refresh 쿠키) → 토큰 재발급(rotation) → 로그아웃 → `get_current_user` 의존성
- 초기 장르 데이터 시드는 게임 CRUD 착수 전까지 진행

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
