# PlayLedger — 데이터 모델 (ERD)

> 작성일: 2026-08-13 / 개정일: 2026-09-18 / 상태: v1.0
> 관련 문서: 요구사항 정의서(01), 시스템 아키텍처(02)

---

## 1. 전체 구조

```mermaid
erDiagram
  USERS ||--o{ REFRESH_TOKENS : "발급"
  USERS ||--o{ OAUTH_ACCOUNTS : "연결"
  USERS ||--o{ ENTRIES : "보유"
  USERS ||--o{ WISHLIST_ITEMS : "관심"
  GAMES ||--o{ ENTRIES : "기록됨"
  GAMES ||--o{ WISHLIST_ITEMS : "담김"
  GAMES ||--o{ GAME_GENRES : "분류"
  GENRES ||--o{ GAME_GENRES : "묶임"
  ENTRIES ||--o{ PLAY_SESSIONS : "플레이"

  USERS {
    integer id PK
    varchar email UK
    varchar steam_id UK
  }
  REFRESH_TOKENS {
    integer id PK
    integer user_id FK
    varchar token_hash UK
  }
  OAUTH_ACCOUNTS {
    integer id PK
    integer user_id FK
    varchar provider
    varchar provider_user_id
  }
  GAMES {
    integer id PK
    varchar title_norm
    integer steam_appid UK
  }
  GENRES {
    integer id PK
    varchar name UK
  }
  GAME_GENRES {
    integer game_id PK, FK
    integer genre_id PK, FK
  }
  ENTRIES {
    integer id PK
    integer user_id FK
    integer game_id FK
  }
  WISHLIST_ITEMS {
    integer id PK
    integer user_id FK
    integer game_id FK
  }
  PLAY_SESSIONS {
    integer id PK
    integer entry_id FK
    date played_on
  }
```

> 다이어그램에는 관계 파악에 필요한 키만 표시한다. 전체 컬럼은 2장 표가 기준이다.

### 관계 요약

| 관계 | 종류 | 의미 |
|---|:---:|---|
| USERS → ENTRIES | 1:N | 사용자 1명이 보유 기록 여러 개를 가진다 |
| USERS → WISHLIST_ITEMS | 1:N | 사용자 1명이 관심 게임 여러 개를 가진다 |
| USERS → REFRESH_TOKENS | 1:N | 기기·브라우저마다 로그인 토큰이 따로 발급된다 |
| USERS → OAUTH_ACCOUNTS | 1:N | 외부 로그인 서비스별로 하나씩 연결된다 |
| GAMES → ENTRIES / WISHLIST_ITEMS | 1:N | 게임 1개가 여러 사용자의 기록·위시리스트에 등장한다 |
| GAMES ↔ GENRES | N:M | 게임 1개에 장르 여러 개, 장르 1개에 게임 여러 개 |
| ENTRIES → PLAY_SESSIONS | 1:N | 보유 기록 1개에 날짜별 플레이 기록 여러 개 |

---

## 2. 테이블 상세

### 2.0 공통 규칙

| 항목 | 규칙 | 이유 |
|---|---|---|
| 시각 | `timestamptz` | 시간대 정보를 함께 저장하고, 화면에 표시할 때 한국 시간으로 변환한다 |
| 코드값 | `varchar` + `CHECK` | PostgreSQL ENUM 타입은 값 추가 시 마이그레이션이 번거롭다 |
| 외부 서비스 ID | 문자열 | Steam·Discord ID는 64비트 정수라 JS 숫자로 다루면 끝자리가 깨진다 |
| `updated_at` 갱신 | ORM(SQLAlchemy)에서 처리 | PostgreSQL에는 MariaDB의 `ON UPDATE CURRENT_TIMESTAMP`가 없다 |
| 값 범위 | DB의 `CHECK`로 강제 | 서버 코드를 거치지 않는 경로(직접 SQL 등)로도 잘못된 값이 들어갈 수 없게 한다 |

**외래키 삭제 규칙**

| 부모 삭제 시 | 자식 테이블 | 규칙 |
|---|---|---|
| 사용자 삭제 | `refresh_tokens`, `oauth_accounts`, `entries`, `wishlist_items` | CASCADE (함께 삭제) |
| 보유 기록 삭제 | `play_sessions` | CASCADE |
| 게임 삭제 | `entries`, `wishlist_items` | RESTRICT (참조 중이면 삭제 거부) |
| 게임·장르 삭제 | `game_genres` | CASCADE |

### 2.1 `users`

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| `id` | integer | PK | |
| `email` | varchar(254) | UNIQUE, NULL | 로그인 ID. 저장 전 소문자로 정규화 |
| `password_hash` | varchar(255) | NULL | 해싱된 비밀번호. Discord 전용 계정은 NULL |
| `nickname` | varchar(30) | NOT NULL | 화면 표시 이름 |
| `steam_id` | varchar(20) | UNIQUE, NULL | Steam 64비트 ID. 연결 안 한 사용자는 NULL |
| `created_at` | timestamptz | NOT NULL | 가입 시각 |

`CHECK (password_hash IS NULL OR email IS NOT NULL)`
비밀번호로 로그인하는 계정은 반드시 이메일이 있어야 한다.

**email을 소문자로 정규화하는 이유**

`Test@a.com`과 `test@a.com`이 서로 다른 계정으로 가입되면 안 된다.
`title_norm`과 같은 원리로, 저장 경로와 무관하게 서버가 항상 소문자로 바꿔 저장한다.

**`steam_id`가 UNIQUE인 이유**

두 계정이 같은 Steam ID를 연결하면, 한 사람의 라이브러리가 두 계정에 복제된다.

### 2.2 `refresh_tokens`

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| `id` | integer | PK | |
| `user_id` | integer | FK → users.id, NOT NULL | |
| `token_hash` | char(64) | UNIQUE, NOT NULL | 토큰 원문의 SHA-256 해시 |
| `expires_at` | timestamptz | NOT NULL | 만료 시각 |
| `revoked_at` | timestamptz | NULL | 폐기 시각. NULL이면 유효 |
| `created_at` | timestamptz | NOT NULL | |

**원문이 아니라 해시를 저장하는 이유**

비밀번호와 같다. DB가 유출돼도 해시만으로는 로그인할 수 없다.
요청으로 들어온 토큰을 해싱해서 `token_hash`와 비교한다.

**지우지 않고 `revoked_at`을 기록하는 이유**

rotation으로 폐기된 토큰이 다시 들어온다면, 누군가 옛 토큰을 훔쳐 쓰고 있다는 신호다.
폐기 기록이 남아 있어야 이를 알아채고 해당 사용자의 토큰을 전부 폐기할 수 있다.

### 2.3 `oauth_accounts`

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| `id` | integer | PK | |
| `user_id` | integer | FK → users.id, NOT NULL | |
| `provider` | varchar(20) | NOT NULL, CHECK | `DISCORD` |
| `provider_user_id` | varchar(32) | NOT NULL | 해당 서비스의 사용자 ID |
| `created_at` | timestamptz | NOT NULL | 연결 시각 |

`(provider, provider_user_id)` 복합 UNIQUE — 같은 Discord 계정이 두 사용자에게 연결될 수 없다.
`(user_id, provider)` 복합 UNIQUE — 한 사용자는 서비스별로 계정 하나만 연결한다.

### 2.4 `games`

게임 자체의 정보. **모든 사용자가 공유하는 마스터 데이터**다.
사용자가 몇 명이든 사이버펑크 2077은 이 테이블에 한 행만 존재한다.

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| `id` | integer | PK | |
| `title` | varchar(200) | NOT NULL | 화면에 표시할 제목 |
| `title_norm` | varchar(200) | NOT NULL, INDEX | 정규화된 제목 (중복 판별용, 서버가 항상 계산) |
| `steam_appid` | integer | UNIQUE, NULL | Steam 고유 ID. 수동 등록 게임은 NULL |
| `released_at` | date | NULL | 출시일 |
| `created_at` | timestamptz | NOT NULL | 등록 시각 |

**`title`과 `title_norm`을 나누는 이유**

같은 게임이 여러 표기로 입력될 수 있다.

| 입력값 | `title_norm` |
|---|---|
| `사이버펑크 2077` | `사이버펑크2077` |
| `Cyberpunk 2077` | `cyberpunk2077` |
| `사이버펑크2077` | `사이버펑크2077` |

정규화 규칙: 공백 제거 → 소문자 변환 → 특수문자 제거.
중복 여부는 항상 `title_norm`으로 판별하고, 화면에는 `title`을 보여준다.

> 한글 표기와 영문 표기는 정규화해도 서로 다른 값이 된다.
> 이 경우까지 잡으려면 별칭(alias) 테이블이 필요하지만,
> MVP 범위에서는 다루지 않는다. (PartScope의 `model_aliases`와 같은 문제)

**중복 판별 순서**

1. `steam_appid`가 있으면 그것으로 비교 (가장 정확)
2. 없으면 `title_norm`으로 비교
3. 둘 다 일치하지 않으면 새 게임으로 등록

### 2.5 `genres` / `game_genres`

장르는 게임과 다대다(N:M) 관계이므로 연결 테이블이 필요하다.

**`genres`**

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| `id` | integer | PK | |
| `name` | varchar(50) | UNIQUE, NOT NULL | 장르명 |

**`game_genres`** (연결 테이블)

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| `game_id` | integer | PK, FK → games.id | |
| `genre_id` | integer | PK, FK → genres.id | |

`(game_id, genre_id)`를 복합 기본키로 쓴다. 같은 짝이 두 번 들어갈 수 없고,
연결 테이블에 따로 `id`를 둘 이유가 없다.

**연결 테이블을 쓰는 이유**

`games` 테이블에 `장르1 / 장르2 / 장르3` 컬럼을 두는 방식은
장르 개수가 고정되고, 장르로 검색할 때 모든 컬럼을 뒤져야 한다.
문자열로 `"RPG, 오픈월드"`처럼 이어 붙이면 DB가 이를 데이터로 인식하지 못해
F-11(장르별 통계)을 구현할 수 없다.

### 2.6 `entries`

특정 사용자가 특정 게임을 보유한 기록. **이 프로젝트의 중심 테이블**이다.

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| `id` | integer | PK | |
| `user_id` | integer | FK → users.id, NOT NULL | |
| `game_id` | integer | FK → games.id, NOT NULL | |
| `status` | varchar(10) | NOT NULL, CHECK | 진행 상태 (아래 참조) |
| `purchased_at` | date | NULL | 구매일 |
| `purchase_price` | integer | NULL, CHECK ≥ 0 | 구매가 (원) |
| `playtime_minutes` | integer | NOT NULL, 기본 0, CHECK ≥ 0 | 총 플레이타임 (분) |
| `rating` | smallint | NULL, CHECK 1~5 | 평점 |
| `review` | varchar(200) | NULL | 한줄평 |
| `source` | varchar(10) | NOT NULL, CHECK | `MANUAL` / `STEAM` |
| `created_at` | timestamptz | NOT NULL | |
| `updated_at` | timestamptz | NOT NULL | 최종 수정 시각 |

`(user_id, game_id)` 복합 UNIQUE. 같은 사용자가 같은 게임을 두 번 등록할 수 없다.

**`status` 값**

| 값 | 의미 | 백로그 분석 대상 |
|---|---|:---:|
| `BACKLOG` | 미시작 | O |
| `PLAYING` | 플레이중 | X |
| `CLEARED` | 클리어 | X |
| `ON_HOLD` | 보류 | O |
| `DROPPED` | 포기 | X |

`ON_HOLD`와 `DROPPED`를 나누는 이유는 분석 대상이 다르기 때문이다.
보류는 돌아올 가능성이 있으니 백로그에 포함하고, 포기는 이미 끝난 것으로 본다.

**`source`가 필요한 이유**

M8에서 Steam 동기화를 실행할 때, 사용자가 직접 수정한 값을
API 응답이 덮어쓰면 안 된다. 동기화 규칙:

- `source = 'STEAM'` → 플레이타임을 API 값으로 갱신
- `source = 'MANUAL'` → 건드리지 않음
- 구매가, 평점, 한줄평은 Steam에 없는 정보이므로 항상 보존

이 컬럼 하나가 "자동 수집 데이터와 수동 데이터의 충돌"이라는
문제 전체를 해결한다.

**타입 선택 근거**

| 컬럼 | 선택 | 이유 |
|---|---|---|
| `playtime_minutes` | 분 단위 정수 | Steam은 분 단위로 응답한다. 시간 단위 소수로 반올림하면 동기화 증가분(세션)을 계산할 때 오차가 누적된다. 화면에는 시간으로 변환해 표시한다 |
| `purchase_price` | integer | 원 단위 정수. 소수점이 필요 없다 |
| `rating` | NULL 허용 | 미평가와 0점은 다르다. 평균 계산 시 NULL은 제외된다 |
| `purchased_at` | NULL 허용 | Steam 동기화로 들어온 게임은 구매일을 알 수 없다 |

> v0에서는 `playtime_hours decimal(6,1)`이었다. 세션 기록(F-20)이 생기면서
> 증가분 계산의 정확도가 중요해져 분 단위 정수로 변경했다.

### 2.7 `wishlist_items`

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| `id` | integer | PK | |
| `user_id` | integer | FK → users.id, NOT NULL | |
| `game_id` | integer | FK → games.id, NOT NULL | |
| `memo` | varchar(200) | NULL | 사고 싶은 이유 등 |
| `created_at` | timestamptz | NOT NULL | 담은 시각 |

`(user_id, game_id)` 복합 UNIQUE.

**`games`를 참조하는 이유**

위시리스트 게임도 장르 정보가 있어야 구매 전 경고(F-18)를 계산할 수 있다.
게임 정보를 따로 저장하지 않고 `games` 마스터를 그대로 재사용한다.

**구매 전환은 트랜잭션으로 처리한다**

`entries`에 추가하는 것과 `wishlist_items`에서 삭제하는 것은 반드시 함께 일어나야 한다.
하나만 성공하면 같은 게임이 양쪽에 동시에 존재하게 된다.

### 2.8 `play_sessions`

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| `id` | integer | PK | |
| `entry_id` | integer | FK → entries.id, NOT NULL | |
| `played_on` | date | NOT NULL | 플레이한 날짜 (한국 시간 기준) |
| `minutes` | integer | NOT NULL, CHECK > 0 | 그날 플레이한 시간 (분) |
| `created_at` | timestamptz | NOT NULL | |

`(entry_id, played_on)` 복합 UNIQUE. 한 게임은 하루에 한 행만 가지고,
같은 날 추가 기록은 기존 행에 합산한다 (3.6절).

**`user_id`와 `source` 컬럼이 없는 이유**

둘 다 `entries`를 따라가면 알 수 있다. 같은 정보를 두 곳에 저장하면
한쪽만 바뀌었을 때 서로 어긋난다. 세션의 출처는 항상 소속된 `entries.source`를 따른다.

---

## 3. 주요 조회 패턴

### 3.1 목록 조회 (F-03)

```sql
SELECT g.title, e.status, e.playtime_minutes, e.purchase_price
FROM entries e
JOIN games g ON g.id = e.game_id
WHERE e.user_id = :user_id
ORDER BY e.updated_at DESC;
```

### 3.2 방치 게임 추출 (F-09)

```sql
SELECT g.title, CURRENT_DATE - e.purchased_at AS idle_days
FROM entries e
JOIN games g ON g.id = e.game_id
WHERE e.user_id = :user_id
  AND e.status = 'BACKLOG'
  AND e.purchased_at IS NOT NULL
ORDER BY idle_days DESC;
```

PostgreSQL은 날짜끼리 빼면 바로 일수(정수)가 나온다. MariaDB의 `DATEDIFF()`에 해당한다.

### 3.3 장르별 통계 (F-11)

```sql
SELECT gn.name,
       COUNT(*)                                     AS total,
       COUNT(*) FILTER (WHERE e.status = 'CLEARED')  AS cleared,
       COUNT(*) FILTER (WHERE e.status <> 'BACKLOG') AS started
FROM entries e
JOIN game_genres gg ON gg.game_id = e.game_id
JOIN genres gn      ON gn.id = gg.genre_id
WHERE e.user_id = :user_id
GROUP BY gn.id;
```

완주율 = `cleared ÷ started` (01 문서 5.3절 정의대로 분모에서 미시작 제외). 계산은 `services`에서 한다.

### 3.4 구매 전 경고 (F-18)

위시리스트 게임의 장르마다, 내가 그 장르를 얼마나 쌓아두고 끝냈는지 조회한다.

```sql
SELECT gn.name,
       COUNT(*) FILTER (WHERE e.status = 'BACKLOG')  AS backlog,
       COUNT(*) FILTER (WHERE e.status = 'CLEARED')  AS cleared,
       COUNT(*) FILTER (WHERE e.status <> 'BACKLOG') AS started
FROM game_genres target
JOIN genres gn      ON gn.id = target.genre_id
JOIN game_genres gg ON gg.genre_id = target.genre_id
JOIN entries e      ON e.game_id = gg.game_id
                   AND e.user_id = :user_id
WHERE target.game_id = :wish_game_id
GROUP BY gn.id;
```

### 3.5 활동 히트맵 (F-20)

```sql
SELECT ps.played_on, SUM(ps.minutes) AS minutes
FROM play_sessions ps
JOIN entries e ON e.id = ps.entry_id
WHERE e.user_id = :user_id
  AND ps.played_on > CURRENT_DATE - 365
GROUP BY ps.played_on
ORDER BY ps.played_on;
```

세션에는 `user_id`가 없으므로 `entries`를 거쳐 사용자를 격리한다.

### 3.6 세션 기록 (같은 날 합산)

```sql
INSERT INTO play_sessions (entry_id, played_on, minutes)
VALUES (:entry_id, :today, :delta)
ON CONFLICT (entry_id, played_on)
DO UPDATE SET minutes = play_sessions.minutes + EXCLUDED.minutes;
```

같은 날 행이 없으면 새로 만들고, 있으면 기존 값에 더한다 (upsert).
하루에 수동 동기화와 자동 동기화가 모두 실행돼도 행이 늘어나지 않는다.

---

## 4. 인덱스 계획

| 테이블 | 컬럼 | 목적 |
|---|---|---|
| `entries` | `(user_id, status)` | 상태별 필터링이 가장 잦은 조회 |
| `entries` | `(user_id, game_id)` UNIQUE | 중복 등록 방지 겸 사용자별 조회 |
| `games` | `title_norm` | 중복 판별 시 매번 조회 |
| `games` | `steam_appid` UNIQUE | 동기화 시 조회 |
| `game_genres` | `genre_id` | 구매 전 경고(3.4절)에서 장르로 게임 찾기 |
| `refresh_tokens` | `user_id` | 사용자 토큰 전체 폐기 |
| `play_sessions` | `(entry_id, played_on)` UNIQUE | upsert 충돌 판정 겸 히트맵 조회 |

**PostgreSQL은 외래키에 인덱스를 자동으로 만들지 않는다.**
MariaDB(InnoDB)는 자동으로 만들어줬지만, PostgreSQL에서는 필요한 곳에 직접 만들어야 한다.

**`game_genres`에 `genre_id` 인덱스가 따로 필요한 이유**

복합 기본키 `(game_id, genre_id)`는 `game_id`로 시작하는 조회에만 쓰인다.
`genre_id`만으로 찾는 조회는 이 순서를 활용할 수 없다.

> PK·UNIQUE 인덱스는 자동으로 생성된다. 나머지는 M4 이후 측정해보고 추가를 결정한다.

---

## 5. 확장 여지 (지금은 안 함)

- **게임 별칭** — 한글·영문 표기를 같은 게임으로 묶는 `game_aliases` 테이블
- **관리자 권한 (F-23)** — `users`에 역할 컬럼 추가
- **커버 아트 (F-22)** — `steam_appid`로 이미지 주소를 계산할 수 있어 컬럼 추가 불필요
- **외부 로그인 추가** — `oauth_accounts.provider`의 허용값만 추가

---

## 변경 이력

| 날짜 | 버전 | 내용 |
|---|---|---|
| 2026-08-13 | v0.1 | 최초 작성 |
| 2026-08-17 | v0.2 | `entries.playtime_hours` 타입을 실제 구현(`models.py`) 기준으로 decimal(7,1) → decimal(6,1) 정정. max_digits=6, decimal_places=1로는 최대 99999.9시간까지 표현 가능해 실사용 범위를 충분히 커버하므로 코드가 아닌 문서를 실물에 맞춤 |
| 2026-09-18 | v1.0 | 스택 전환(MariaDB → PostgreSQL)에 따른 전면 개정. 파일명 `ERD.md` → `03_erd.md`. `refresh_tokens`·`oauth_accounts`·`wishlist_items`·`play_sessions` 추가, 로그인 ID를 email로 변경, `playtime_hours`(decimal) → `playtime_minutes`(integer), 공통 규칙(2.0)과 외래키 삭제 규칙 신설, 조회 쿼리를 PostgreSQL 문법으로 변경. 개정 전 문서는 `v0-rn-django` 태그 참고 |
