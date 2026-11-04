# PLAYLEDGER — DEVLOG

> **세션마다 겪은 일 · 막힌 일 · 배운 것**을 적는다. **최신이 위.** 지난 기록은 고치지 않고 위에 덧붙인다.
> 진행 상황 · 완료 기준은 [PLAN](PLAN.md), 결정의 이유는 [decisions/](decisions/README.md). 끝난 단계는 맨 아래 표에서 [archive/](archive/README.md)로.

## 현재 상태

| 항목 | 내용 |
|---|---|
| 단계 | **M5** 🔄 배포 (`PLAN` M5). `v1.0.0` 태그 있음. **`https://play.sagming.com` 운영 중**, 배포된 커밋 `e1e368c` |
| 진행 중 | 없음. 미커밋 없음 |
| 다음에 할 일 | ① 클린룸: **사용자가 집 PC에서 저장소를 지우고 새로 받아 직접** 한다(아래 집 PC 칸). Claude가 대신 돌리지 않는다 ② 코드: 서버 감시 `uptime.yml`, HSTS 1년, 개인정보 안내에 백업 14일 · Vultr 서울 · 접속 기록 반영 → 배포 ③ 운영 백업으로 복구 리허설(열쇠가 회사 PC에만 있다) ④ 200개 목록 측정 ⑤ 되돌리기 시험을 할지 사용자에게 묻는다 ⑥ `DESIGN` · `REQUIREMENTS` 대조 후 M5 ✅. 작업 방식은 정해졌다: 코드 · 문서는 Claude 자동, 서버 명령은 사용자가 친다. **Vultr 크레딧 2026-11-30 만료, 12월 AWS 이사** |
| 판단이 남은 것 | 모바일 첫 줄이 요약 줄 도착 때 24px 밀리는 것. S-05 방치 일수 색(180일 미만도 포인트 색). 개인정보 안내 문구(법률 검토 안 받음). 아이폰 확인. 백업 개인키 사본(`SERVER` 3.7절) |
| 기기별로 할 일 | **집 PC** 클린룸: 지우기 전에 `git status` · `git log origin/main..`으로 안 올린 작업 확인. `.env`는 폴더와 함께 사라지는데 Docker 볼륨 `pgdata`는 남는다 ─ 예전 비밀번호를 쓰거나 볼륨까지 지운다(그러면 확인용 기록도 사라진다). 그다음 `README` "시작하기"대로, 확인은 `pytest`(310건) · `npm test`(202건). **노트북**: `git pull` → `server/`에서 `pip install -r requirements-dev.txt` · `alembic upgrade head` → `web/`에서 `npm ci`(글꼴 패키지 2개 추가). `JWT_SECRET_KEY`가 32자 미만이면 서버가 뜨지 않는다. **서버 접속이 필요한 기기**: 열쇠를 새로 넣어야 한다(`SERVER` 3.1절). 지금은 회사 PC만 들어간다 |
| 집 PC에만 있는 것 | 개발 DB의 확인용 계정 1개 · 기록 3개(클린룸에서 볼륨을 지우면 사라진다). `.claude/launch.json`은 절대 경로가 있어 커밋하지 않았다 ─ 다른 기기에서 미리보기를 쓰려면 새로 만든다 |
| 회사 PC에만 있는 것 | `play-1` SSH 열쇠(`~/.ssh/play_vultr`) · **백업 개인키**(`~/playledger-backup.key`). `.claude/worktrees/brave-hawking-fc3e7c`(병합됨, 지워도 된다). 헤드리스 Edge 확인 스크립트는 저장소에 없다 ─ 필요하면 [DEVLOG_M4.5](archive/DEVLOG_M4.5.md)를 보고 새로 만든다 |

## 작성 규칙

- 형식은 전역 설정 "문서 체계" 절을 따른다: `## YYYY-MM-DD (n) · 제목 (기기)` → 한 일 / `[설계]` / 막힌 것(증상 · 원인 · 해결 · 배운 것) / 이번 세션 커밋 / 다음에 할 일. 2026-11-02 이전 블록은 옛 형식 그대로 둔다
- 기기 표기는 `README` 개발 환경 표를 따른다 (데스크톱 A · 데스크톱 B · 노트북)
- **막혔던 점은 해결됐어도 반드시 남긴다.** 같은 실수를 반복하지 않기 위한 기록이고, 나중에 이 프로젝트를 설명할 때 "어떤 문제를 어떻게 해결했는가"가 결과물보다 더 중요한 이야기가 된다
- 환경 버전은 여기 적지 않는다. `requirements.txt` · `package.json` · `ci.yml`이 원본이고, 기기별 런타임은 `README`에 있다

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
