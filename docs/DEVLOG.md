# PlayLedger — DEVLOG

> 세션별 개발 회고 및 트러블슈팅 기록

이 문서는 마일스톤 문서(`05_milestones.md`)처럼 "계획"을 담는 곳이 아니라,
**실제로 각 세션에서 무슨 일이 있었는지**를 기록하는 곳이다.
막혔던 지점, 해결한 방법, 다음에 참고할 만한 실수 등을 가감 없이 남긴다.

---

## 현재 상태

**진행 중** · M1 (백엔드 기초) 착수 예정

**환경 요약**
| 항목 | 값 |
|---|---|
| Python | 3.13.5 |
| Django | 6.1 |
| Node.js | v24.15.0 |
| React Native | 0.87.0 (CLI) |
| MariaDB | 12.2.2 |
| RN 환경 | **React Native CLI로 확정** (Expo 아님 — 안드로이드 스튜디오 기설치, USB 실기기 연결 환경이라 CLI가 더 자연스러움) |
| 테스트 기기 | 실기기 (갤럭시 S25 Edge, USB 디버깅) |
 
**다음에 할 일** · M1 착수 — ERD 기준 Django 모델 정의 (`accounts`, `library` 앱)

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
  원인: 콜레이션 이름 오타 (`utfmb4` → `utf8mb4` 누락)
  해결: `utf8mb4_unicode_ci`로 정정 후 재실행
  교훈: `utf8mb4` 관련 옵션은 철자 하나만 틀려도 조용히 실패하지 않고 바로 에러로 잡히니, 에러 메시지를 그대로 믿고 다시 치면 됨
- 증상: `adb devices`에 기기가 `unauthorized`로만 표시됨
  원인: 폰에서 "USB 디버깅 허용" 팝업을 아직 승인하지 않음
  해결: 폰 화면 잠금 해제 후 팝업에서 "이 컴퓨터에서 항상 허용" 체크 후 허용
  교훈: PC에서의 인식(daemon 연결)과 폰에서의 인증(authorized)은 별개 단계. `unauthorized`가 뜨면 폰 쪽 조작이 필요하다는 신호
- 증상: `run-android`는 `BUILD SUCCESSFUL`인데 폰에 빨간 에러 화면(`Unable to load script`)
  원인: 네이티브 빌드(APK 설치)와 JS 번들 서버(Metro)는 별개 프로세스인데, Metro가 자동으로 안 켜짐
  해결: 별도 터미널에서 `npx react-native start`로 Metro 수동 실행 후 앱 재시작
  교훈: RN은 "네이티브 껍데기 설치"와 "JS 코드 제공"이 분리된 구조. 둘 다 확인해야 함. 앞으로는 항상 Metro(터미널 1)를 먼저 켜두고 `run-android`(터미널 2)를 실행하는 순서로 진행
- 증상: RN 프로젝트 생성 로그에 `Initializing Git repository`가 찍힘
  원인: RN CLI가 `app/` 폴더 안에 독자적인 `.git`을 새로 만듦 (루트 저장소와 중첩)
  해결: `app/.git` 폴더 삭제 후 `git status`로 루트 저장소에 정상 편입됐는지 확인
  교훈: 하위 폴더에 프로젝트를 생성하는 CLI 도구는 자체적으로 Git 저장소를 만드는 경우가 있으니, 생성 직후 반드시 `.git` 중첩 여부 확인할 것

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
