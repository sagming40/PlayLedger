# PlayLedger — DEVLOG

> 세션별 개발 회고 및 트러블슈팅 기록

이 문서는 마일스톤 문서(`05_milestones.md`)처럼 "계획"을 담는 곳이 아니라,
**실제로 각 세션에서 무슨 일이 있었는지**를 기록하는 곳이다.
막혔던 지점, 해결한 방법, 다음에 참고할 만한 실수 등을 가감 없이 남긴다.

---

## 현재 상태

**진행 중** · M2 (앱 연동) — React Navigation 설치 및 네비게이션 골격(하단 탭 + 라이브러리 스택 + 로그인 분기) 완료. 다음은 API 호출 모듈 작성

**환경 요약**
| 항목 | 값 |
|---|---|
| Python | 3.13.5 |
| Django | 6.1 |
| Node.js | v24.15.0 |
| React Native | 0.87.0 (CLI) |
| MariaDB | 12.2.2 |
| React Navigation | @react-navigation/native 7.3.16, bottom-tabs 7.18.16, native-stack 7.18.8 |
| react-native-screens | 4.27.0 |
| react-native-safe-area-context | 5.9.0 |
| RN 환경 | React Native CLI로 확정 |
| 테스트 기기 | 실기기 (갤럭시 S25 Edge, USB 디버깅), Android Studio 에뮬레이터(Pixel 8, API 37.1) |

**다음에 할 일** · API 호출 모듈 작성 (api/ — 서버 주소, 토큰 첨부 한 곳에) 착수. `03_api_spec.md`는 이 작업 시작 시점에 함께 쓰는 게 자연스러움 (실제 호출할 엔드포인트를 코드로 확인하며 작성)

---

## 작성 규칙

- 세션(하루 작업 단위) 종료 시 또는 마일스톤 완료 시 기록
- 최신 항목이 위로 오도록 역순 정렬
- 형식: 날짜 / 관련 마일스톤 / 한 일 / 막혔던 점 / 다음에 할 일

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
