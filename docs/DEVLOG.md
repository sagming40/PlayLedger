# PlayLedger — DEVLOG

> 세션별 개발 회고 및 트러블슈팅 기록

이 문서는 마일스톤 문서(`05_milestones.md`)처럼 "계획"을 담는 곳이 아니라,
**실제로 각 세션에서 무슨 일이 있었는지**를 기록하는 곳이다.
막혔던 지점, 해결한 방법, 다음에 참고할 만한 실수 등을 가감 없이 남긴다.

---

## 현재 상태

**진행 중** · M1 (백엔드 기초) — 인증 파트 3/4 완료 (DRF 설정·회원가입·로그인), 권한 클래스 검증은 게임 CRUD와 함께 다음 세션에서 확인 예정

**환경 요약**
| 항목 | 값 |
|---|---|
| Python | 3.13.5 |
| Django | 6.1 |
| Node.js | v24.15.0 |
| React Native | 0.87.0 (CLI) |
| MariaDB | 12.2.2 |
| RN 환경 | React Native CLI로 확정 |
| 테스트 기기 | 실기기 (갤럭시 S25 Edge, USB 디버깅) |

**다음에 할 일** · M1 게임 CRUD 착수 — Serializer 작성, 목록 조회, 등록(중복 판별), 단건 조회/수정/삭제, 사용자 격리 확인. CRUD 완성 시 권한 클래스(비로그인 차단) 실증 테스트도 함께 진행

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
