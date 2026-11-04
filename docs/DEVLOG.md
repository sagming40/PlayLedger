# PLAYLEDGER — DEVLOG

> **세션마다 겪은 일 · 막힌 일 · 배운 것**을 적는다. **최신이 위.** 지난 기록은 고치지 않고 위에 덧붙인다.
> 진행 상황 · 완료 기준은 [PLAN](PLAN.md), 결정의 이유는 [decisions/](decisions/README.md). 끝난 단계는 맨 아래 표에서 [archive/](archive/README.md)로.

## 현재 상태

| 항목 | 내용 |
|---|---|
| 단계 | **M5** 🔄 배포 (`PLAN` M5). `v1.0.0` 태그 있음. **`https://play.sagming.com` 운영 중**, 배포된 커밋 `f463a1b` |
| 진행 중 | 없음. 미커밋 없음 |
| 다음에 할 일 | ⓪ `task deploy`를 실제 서버로 처음 돌린다. 사용자가 친다(아래 2026-11-05 (1)) ① 서버 열쇠: 노트북에서 `play_vultr`(`-C laptop`)를 만들고 공개키를 넣는다(`SERVER` 3.1절, 집 PC는 끝남). 사용자가 친다 ② 코드: 서버 감시 `uptime.yml`, HSTS 1년, CSP `img-src` 좁히기, 개인정보 안내에 백업 14일 · Vultr 서울 · 접속 기록 반영 → 배포 ③ 재부팅 뒤 자동 복구 확인 ④ 운영 백업으로 복구 리허설(열쇠가 회사 PC에만 있다) ⑤ 200개 목록 측정 ⑥ 되돌리기 시험을 할지 사용자에게 묻는다 ⑦ `DESIGN` · `REQUIREMENTS` 대조 후 M5 ✅. 코드 · 문서는 Claude 자동, 서버 명령은 사용자가 친다. **Vultr 크레딧 2026-11-30 만료, 12월 AWS 이사** |
| 판단이 남은 것 | 모바일 첫 줄이 요약 줄 도착 때 24px 밀리는 것. S-05 방치 일수 색(180일 미만도 포인트 색). 개인정보 안내 문구(법률 검토 안 받음). 아이폰 확인. 비밀번호 보기 버튼을 Edge · 실제 폰에서 아직 안 봤다(운영에는 올라감). 백업 개인키 사본(`SERVER` 3.7절) |
| 기기별로 할 일 | **노트북**: `git pull` → `server/`에서 `pip install -r requirements-dev.txt` · `alembic upgrade head` → `web/`에서 `npm ci`(글꼴 패키지 2개 추가). `JWT_SECRET_KEY`가 32자 미만이면 서버가 뜨지 않는다. **서버 접속**: 회사 PC · 집 PC는 된다. 노트북은 아직(위 ①) |
| 집 PC에만 있는 것 | `play-1` SSH 열쇠(`~/.ssh/play_vultr`, 회사 PC 것과 별개). 클린룸으로 새로 만든 개발 DB(확인용 계정 · 게임 기록). `.claude/launch.json`은 실행 중인 `5173`에 붙기만 하는 설정으로 새로 만들었다(커밋 안 함) |
| 회사 PC에만 있는 것 | **백업 개인키**(`~/playledger-backup.key`). `.claude/worktrees/brave-hawking-fc3e7c`(병합됨, 지워도 된다). 헤드리스 Edge 확인 스크립트는 저장소에 없다 ─ 필요하면 [DEVLOG_M4.5](archive/DEVLOG_M4.5.md)를 보고 새로 만든다 |

## 작성 규칙

- 형식은 전역 설정 "문서 체계" 절을 따른다: `## YYYY-MM-DD (n) · 제목 (기기)` → 한 일 / `[설계]` / 막힌 것(증상 · 원인 · 해결 · 배운 것) / 이번 세션 커밋 / 다음에 할 일. 2026-11-02 이전 블록은 옛 형식 그대로 둔다
- 기기 표기는 `README` 개발 환경 표를 따른다 (데스크톱 A · 데스크톱 B · 노트북)
- **막혔던 점은 해결됐어도 반드시 남긴다.** 같은 실수를 반복하지 않기 위한 기록이고, 나중에 이 프로젝트를 설명할 때 "어떤 문제를 어떻게 해결했는가"가 결과물보다 더 중요한 이야기가 된다
- 환경 버전은 여기 적지 않는다. `requirements.txt` · `package.json` · `ci.yml`이 원본이고, 기기별 런타임은 `README`에 있다

---

## 2026-11-05 (1) · 집 PC 작업 확인, `task deploy` (데스크톱 B, 자동)

### 한 일
- 진행 순서: 집 PC 작업 확인 → `cbt-journal` 스크립트 · `play-release` 읽기 → 설계 → 작성 → 임시 클론에서 실패 경로 → 커밋 · push → 실제 대기 경로 → 문서
- 집 PC 작업 확인: 어제 커밋의 CI 모두 `success`, `f463a1b` ~ `26341bf` 사이 `web` · `server` · `deploy` 변경 없음, 회사 PC에서 lint · `format:check` · `vue-tsc` 통과, `npm test` 202 passed
- 어제 못 본 로그인 화면의 보기 버튼을 운영 `/login`에서 확인: `password` → `text` → `password`, 라벨 · `aria-pressed` 변경, 포커스 유지(스크립트로 보낸 이벤트), 버튼 44×46px, 칸 오른쪽 여백 44px. 로그인 칸에 `maxlength`가 없는 것은 원래 그렇다
- `scripts/deploy.ps1` · `Taskfile.yml`, `SERVER` 2절. `README`에는 배포 명령이 없고 `SERVER`를 가리키기만 해서 고칠 곳이 없었다

### [설계]
- 위치는 `scripts/`: `deploy/`는 서버에 올라가는 파일이다. `Taskfile.yml`도 둔다 ─ 회사 PC Task 3.54.0, 집 PC · 노트북은 `cbt-journal` 때문에 있을 것(확인 안 함)
- **CI가 도는 중이면 기다린다**(최대 10분, 30초 간격). 어제 멈칫한 경우가 바로 이것이고, CI가 100 ~ 132초라 push하고 바로 쳐도 된다. 로그인 없는 GitHub API는 시간당 60번이라 간격을 넓혔다
- 사전 검증에서 발견: 기다리는 동안 다른 기기가 push하면 옛 커밋으로 운영을 덮어쓴다 ─ 기다린 뒤 깨끗함 · `origin/main` 비교를 다시 한다
- 사전 검증에서 발견: `audit`만 실패한 커밋은 이미지가 있어도 run 결과가 `failure`다. 멈추는 쪽으로 뒀다 ─ 취약점을 보고 올릴지는 사람이 정하고, 그때는 `play-release`를 직접 부른다
- CI 상태를 못 읽으면 통과로 치지 않고 멈춘다. `-SshHost`는 `cbt-journal`과 같은 옵션인데, 운영을 건드리지 않고 ssh 실패 경로를 시험하는 데도 썼다
- 빌드 · 복사가 없어 `cbt-journal`보다 훨씬 짧다. 이미지는 CI가 만든다

### 막힌 것
- **커밋 메시지의 큰따옴표로 `git commit`이 실패.** 증상: `error: pathspec 'play-release' did not match`. 원인: Windows PowerShell 5.1이 인자 속 `"`를 그대로 넘겨 `-m` 내용이 쪼개졌다. 해결: 메시지를 파일로 써서 `git commit -F`. 커밋 전이라 들어간 것은 없다
- **CI 실행이 생각보다 늦게 보인다.** push 뒤 API에서 30초에 없고 60초에 보였다. "없음" 판정 90초는 여유가 작아 180초로 늘렸다(판정이 틀려도 멈출 뿐 배포되지는 않는다)

### 확인
- 임시 클론(bare + clone, 실제 저장소 · 서버 안 건드림)에서 `deploy.ps1` 실행. 90초 판정일 때 시험한 것이다

| 경우 | 결과 |
|---|---|
| 정상 + `-DryRun` | exit 0, 실행할 ssh 명령 출력 |
| 새 파일이 있음 | exit 1 |
| push 안 한 커밋 / 뒤처진 커밋 | exit 1 / exit 1 |
| CI 실패 커밋 `8c66e97` | exit 1, `ci 결과가 failure` |
| GitHub에 없는 커밋 | 91초 뒤 exit 1, `ci 실행이 없다` |
| 없는 ssh 별명 | ssh 255 → exit 1 |
| 도는 중인 `25fef04`, 기다리는 사이 origin 변경 | 60 ~ 121초 대기 → ci 성공 → 커밋 다름으로 exit 1 |

- 실제 저장소에서 `task deploy -- -DryRun`: exit 0, 저장소 깨끗함. 한글 출력 정상, BOM은 커밋 · 클론 뒤에도 남음(LF인 채로 5.1에서 돈다)
- **확인 못 한 것**: 실제 서버로 배포(passphrase · sudo 비밀번호가 필요해 사용자가 친다), GitHub API가 막혔을 때 멈추는 경로, 180초로 늘린 값 자체

### 이번 세션 커밋
- `feat(M5)` `task deploy` `25fef04` / `docs(M5)` 런북 · 기록, "없음" 판정 180초

### 다음에 할 일
- "현재 상태" ⓪ ~ ⑦

---

## 2026-11-04 (11) · 클린룸 검증, 비밀번호 보기 버튼 (데스크톱 A, 클린룸은 사용자 · 문서와 코드는 자동)

### 한 일
- 진행 순서: 안 올린 작업 확인 → 사용자가 볼륨까지 지우고 새로 클론 → `README`만 보고 실행 → 발견 정리 → 문서 수정 → 비밀번호 보기 버튼
- 클린룸(사용자가 직접): `docker compose down -v` → 폴더 삭제 → 클론 → `README` "시작하기". `pytest` **310 passed**(38.89초), `npm run lint` · `format:check` · `vue-tsc` 통과, `npm test` **202 passed**, 화면에서 가입 · 게임 등록
- 집 PC 서버 열쇠: 회사 PC 없이 Vultr 웹 콘솔로 공개키를 넣었다. `ssh play` → `sudo whoami` = root (`SERVER` 5절)
- 클린룸 발견 4건을 `README`에서 고침
  1. `web/` 검사 명령(lint · format:check · vue-tsc · test)이 `README`에 없었다. CLAUDE.md에만 있었다
  2. `pytest`가 `requirements-dev.txt`에 있다는 안내가 테스트 절에 없었다
  3. 개발 환경 표의 데스크톱 A Python이 3.13.5 ─ 실제는 3.14.7(Miniconda)
  4. "배포 구성은 M5에서 작성됩니다" ─ 이미 `docs/SERVER.md`가 있다
- 비밀번호 보기 버튼 `PasswordInput.vue`: 로그인 · 계정 삭제 칸 (`DESIGN` 3.1절)
- 외부 리뷰(사용자가 ChatGPT에 맡긴 종합 평가)를 코드와 대조해 PLAN M5에 두 항목 추가: 재부팅 뒤 자동 복구, CSP `img-src` 좁히기. 나머지 권고는 이미 M5 · M6 계획에 있었다

### [설계]
- 닉네임은 중복 허용 그대로 둔다(`DATA_MODEL` 2.1절). 사용자가 같은 닉네임 가입을 보고 물었다 ─ 기기마다 DB가 따로이기도 하고, 닉네임은 표시 이름이다
- 게임별 리뷰 · 댓글은 `REQUIREMENTS` F-34로만 적었다. 3.2절 "소셜 기능은 하지 않는다"와 부딪쳐서, 하게 되면 `decisions/`부터
- 비밀번호 보기 버튼은 4.4절에 적지 않고 바로 넣었다. 사용자가 요청했고 화면 두 곳 · 컴포넌트 하나라 작다
- 버튼은 `type="button"`(폼 제출 방지), `mousedown.prevent`(칸 포커스 유지 ─ 모바일 키보드가 닫히지 않게), `aria-pressed` · 바뀌는 `aria-label`. Edge의 `::-ms-reveal`을 숨겨 눈이 두 개 보이지 않게
- 대화상자를 닫으면 컴포넌트가 사라져 다음에 열 때 가려진 상태로 시작한다 ─ 따로 되돌리는 코드를 두지 않았다
- PC 쪽 배포 스크립트를 만들기로 했다(다음 세션, 회사 PC). 사용자가 `cbt-journal`은 `task deploy` 한 줄인데 왜 다르냐고 물었다 ─ 스택 차이가 아니라 단축 스크립트를 안 만든 차이다. 정해 둔 것:
  - 확인 순서: 미커밋 없음 → `origin/main`과 같음 → GitHub Actions에서 그 커밋의 `ci`가 `success`(저장소가 공개라 토큰 없이 `api.github.com/repos/sagming40/PlayLedger/actions/runs?head_sha=…`로 볼 수 있다) → 통과하면 `ssh -t play "sudo play-release <전체 커밋>"`. 하나라도 아니면 이유를 말하고 멈춘다
  - 정할 것: 파일 위치(`scripts/deploy.ps1` 새 폴더 vs `deploy/`. `deploy/`는 서버에 올라가는 파일이라 섞지 않는 쪽이 낫다), `Taskfile.yml`도 둘지(Task는 `cbt-journal` 때문에 기기마다 깔려 있는지 확인), `-DryRun`, CI가 아직 도는 중이면 기다릴지 멈출지
  - 끝나면 `SERVER` 2절 배포 명령과 `README`를 바꾼다
- 가입 409 "이미 사용 중인 이메일"이 계정 존재를 알려 준다는 리뷰 지적은 이미 `ARCHITECTURE` 3.10절 · F-27에 감수한 것으로 적혀 있다

### 막힌 것
- **`pytest`를 찾을 수 없음.** 증상: venv에서 `pytest` → CommandNotFoundException. 원인: `requirements.txt`만 설치됨. `README` 2번에는 `requirements-dev.txt`가 맞게 있었지만 바로 옆 "운영은 requirements.txt만" 주석과 테스트 절에 안내가 없어 놓치기 쉬웠다. 해결: `pip install -r requirements-dev.txt` 후 310 passed, 테스트 절에 한 줄 추가
- **`ssh play "sudo play-compose ps"`가 sudo 비밀번호를 못 받음.** 원인: Claude가 안내한 명령에 `-t`가 빠졌다. 터미널이 없으면 sudo가 비밀번호를 묻지 못한다. 해결: 한 줄로 칠 때는 `ssh -t play "sudo …"`(배포 명령처럼). 이번에는 `play-release` 출력에 세 컨테이너 Healthy가 이미 있어 따로 안 봐도 됐다
- `npm run format check`(콜론 없이)를 쳐서 `prettier --write`가 돌았다. 전부 `unchanged`라 바뀐 파일은 없었다
- 새 컴포넌트가 처음에 `format:check`에서 걸렸다. 커밋 전에 검사를 `&&`로 묶어 돌려서 잡았다(앞 세션 교훈)

### 확인
- `npm run lint` · `format:check` · `vue-tsc` 통과, `npm test` 202 passed (컴포넌트 테스트 도구가 없어 이 버튼의 자동 테스트는 없다)
- 화면(내장 브라우저, 설정 → 계정 삭제 대화상자, 삭제는 누르지 않음): 처음 `type=password` · "비밀번호 보기" · 버튼 44×46px · 칸 오른쪽 여백 44px · `autocomplete=current-password` · `maxlength=128` 유지. 누르면 `type=text` · "비밀번호 숨기기" · `aria-pressed=true`, 포커스는 칸에 그대로, 값 유지, 대화상자 열린 채. 다시 누르면 password. 닫았다 열면 password · 빈 값
- **확인 못 한 것**: 로그인 화면(브라우저가 로그인 상태라 직접 열지 않음, 같은 컴포넌트), Edge에서 눈이 하나만 보이는지, 실제 폰

### 이번 세션 커밋
- `feat(M5)` 비밀번호 보기 버튼 / `docs(M5)` 클린룸 발견 · 닉네임 · F-34 · M5 항목

### 다음에 할 일
- "현재 상태" ① ~ ⑦

---

## 2026-11-04 (10) · M5 첫 배포, play.sagming.com 운영 시작 (데스크톱 B, 코드 자동 · 서버 명령 사용자)

### 한 일
- 진행 순서: 글꼴 내장 + CSP 준비 → 이미지 · 운영 Compose · Caddy를 로컬에서 확인 → CI 이미지 · 배포 · 백업 스크립트 → 서버 세팅 + DNS → 첫 배포 → LTE · 요청 제한 · 계정 삭제 확인 → 화면 수정 후 두 번째 배포
- 글꼴을 `@fontsource-variable`로 내장, 인라인 테마 스크립트를 `public/theme-init.js`로
- `server/Dockerfile` · `web/Dockerfile` · `web/deploy/Caddyfile` · `deploy/`, CI `images` 작업, `docs/SERVER.md`
- 밝은 커버에서 상세 화면 위쪽 글자가 안 보이던 것을 실제 폰으로 발견해 고침
- 관찰값은 `SERVER` 5절

### [설계]
- 새 서버 `play-1`: 공개 가입 앱을 개인 기록 앱 `cbt-1`과 분리
- Caddy도 컨테이너로: 서버에는 Docker만 있으면 되어 12월 이사가 쉽다. `cbt-journal`의 호스트 Caddy와 다르다
- 이미지는 CI가 전체 커밋 번호 태그로 만들고 서버는 받기만 한다. 실패한 커밋은 배포할 수 없고, SSH 키를 GitHub에 맡기지 않는다. GHCR은 로그인 없이 받아져 서버에 토큰이 없다
- DB는 내부 망만, API 포트는 밖으로 안 연다. Caddy IP를 고정해 그 주소의 `X-Forwarded-For`만 믿는다
- 백업에서 `steam_apps` 내용은 뺀다(공개 목록이고 미러링으로 다시 만든다)
- 사전 검증에서 발견: `/docs`는 Caddy가 `/api`만 넘겨서 404가 아니라 앱의 없는 주소 화면(200)이다 ─ 완료 기준을 고쳤다. 인라인 스크립트가 CSP에 막히는 것도 미리 파일로 뺐다

### 막힌 것
- **`play-1` 비밀값이 대화에 노출.** 증상: `.env`를 nano로 연 캡처에 DB 비밀번호 · JWT 비밀이 찍힘. 해결: DB를 만들기 전이라 둘 다 새로 생성. 배운 것: 안내에 "캡처 금지"를 써도 부족하다 ─ 값이 보이는 화면을 열게 하지 않는 절차로 만든다
- **lint 실패를 통과로 적음.** `7189c6a` 설명의 eslint 통과는 틀렸다. 출력 끝줄만 봤고 `theme-init.js`의 no-undef를 CI가 잡았다. `public/`을 lint에서 제외
- **format 실패인 채 커밋 · push.** `8c66e97`. 검사와 커밋을 `;`로 묶어서 `format 1`을 보고도 커밋됐다. `e1e368c`로 정리. 배운 것: 커밋은 검사를 `&&`로 묶고, 결과는 종료 코드로 본다
- **CI audit · 첫 이미지**: 위 lint 때문에 첫 이미지가 안 만들어져 익명 pull이 denied로 보였다. 이미지가 생긴 뒤 200이었다
- Vultr 화면에서 SSH 공개키를 입력칸에 넣기만 하면 사라졌다(사용자가 해결)
- 사용자가 서버 탭에서 `notepad`를 침 ─ 프롬프트로 탭을 구분하도록 `SERVER` 4절에 적음

### 이번 세션 커밋
- `feat(M5)` 글꼴 내장 `7189c6a`, 운영 이미지 `eec37b7`, 배포 · 백업 스크립트 `b3e0ee7` / `ci(M5)` 이미지 / `docs(M5)` 런북 / `fix(M5)` lint `fd07964`, 밝은 커버 `8c66e97` · `e1e368c`

### 다음에 할 일
- "현재 상태" ① ~ ⑥

---

## 끝난 단계

단계가 끝나면 날짜 블록을 [archive/](archive/README.md)로 옮기고 여기에는 한 줄만 남긴다.

| 단계 | 기간 | 한 줄 요약 | 블록 |
|---|---|---|---|
| M4.5 배포 전 정비 | 2026-11-04 | 서버 구멍 · 직접 등록 게임 분리 · 계정 삭제 · 탭 간 재발급 · 오류 처리 · CI 취약점 검사 · v1.0 독립 대조, `pytest` 310건 · `npm test` 202건 | [DEVLOG_M4.5](archive/DEVLOG_M4.5.md) |
| M4 통계 대시보드 | 2026-11-04 | 통계 API · S-05 화면 · 예시 데이터 · 손계산 대조, `npm audit` 정리 | [DEVLOG_M4](archive/DEVLOG_M4.md) |
| M3 상태 관리 + 평점 | 2026-11-03 ~ 11-04 | 상세 · 상태 · 평점 바로 고치기, 필터 · 주소 쿼리, 수정 · 삭제, 저장 알림, 수정 · 삭제 동시 실행 500 수정 | [DEVLOG_M3](archive/DEVLOG_M3.md) |
| M2 프론트 연동 · M2.5 Steam 검색 | 2026-09-28 ~ 11-03 | 로그인 · 목록 · 등록 · 설정 화면, 다크 · 라이트, Steam 검색 등록 · 커버, 상단 메뉴, ESLint · Prettier | [DEVLOG_M2](archive/DEVLOG_M2.md) |
| M1 백엔드 기초 | 2026-09-19 ~ 09-28 | 인증 · 보유 기록 CRUD · pytest 19건 · GitHub Actions · API 계약 문서 | [DEVLOG_M1](archive/DEVLOG_M1.md) |
| M0 환경 구성 | 2026-09-18 ~ 09-19 | 스택 전환 결정, Compose · FastAPI · Vue로 화면 → 서버 → DB 연결 | [DEVLOG_M0](archive/DEVLOG_M0.md) |
| v0 (옛 스택) | 2026-08-13 ~ 08-17 | RN + Django + MariaDB. 태그 `v0-rn-django` | [DEVLOG_v0](archive/DEVLOG_v0.md) |
