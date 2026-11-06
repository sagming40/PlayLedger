# PLAYLEDGER — DEVLOG

> **세션마다 겪은 일 · 막힌 일 · 배운 것**을 적는다. **최신이 위.** 지난 기록은 고치지 않고 위에 덧붙인다.
> 진행 상황 · 완료 기준은 [PLAN](PLAN.md), 결정의 이유는 [decisions/](decisions/README.md). 끝난 단계는 맨 아래 표에서 [archive/](archive/README.md)로.

## 현재 상태

| 항목 | 내용 |
|---|---|
| 단계 | **M5 ✅ 2026-11-06** (기록은 [DEVLOG_M5](archive/DEVLOG_M5.md), 닫기 전 점검 표는 그 파일 2026-11-06 (6)). **M6 🔄 Steam 동기화** ─ 번호를 다시 매겼다(2026-11-06 (8), [decisions/0017](decisions/0017-milestone-renumber.md)): M6 Steam 동기화 → M7 자동 동기화 → M8 Discord → 확장 M9 · M10 · M11(순서 없음). 옛 번호는 [archive/README](archive/README.md) 대응표. M5.5 서버 이사는 12월. `v1.0.0` 태그 있음. **`https://play.sagming.com` 운영 중**, 배포된 커밋 `c34b701` (`task deploy`) |
| 진행 중 | **M6 Steam 계정 연결(서버)은 끝, 운영 배포 전 ─ 다음은 보유 게임 목록(`GetOwnedGames`)**(2026-11-06 (11)). 화면 버튼(S-06)은 아직 없어서 `/settings?steam=` 결과를 화면이 안 읽는다. 방식: 마이그레이션까지 사용자가 직접 쳤고 그 뒤로는 **자동**(사용자 지시). 먼저 읽을 것: `PLAN` M6 작업 목록, [decisions/0016](decisions/0016-steam-sync-details-later.md) · [0019](decisions/0019-steam-purchase-info.md), `ARCHITECTURE` 5.1 · 5.4절. 운영 중인 것: 매일 백업(서버 14개 + R2 14일) · 디스크 감시(`/api/health` `disk`) · Steam 매주 타이머 · `uptime`. R2 14일 정리가 실제로 지우는 것은 11-20 이후에 처음 본다. `uptime` 예약 실행은 지금까지 3번(11-05 22:28 · 11-06 05:48 · 10:29 KST) ─ 30분마다인데 하루 몇 번만 돌아서 며칠 지켜본다 |
| 다음에 할 일 | ① `uptime` 실행 간격을 며칠 지켜본다, 새 "디스크 여유" 단계가 통과하는지 본다 ② 11-08(일) 아침 `journalctl -u play-steam-sync`로 첫 예약 실행을 본다 ③ 11-20 이후 R2 버킷에서 14일 지난 사본이 지워졌는지 본다(`SERVER` 5절 맨 아래) ④ M6 `PLAN` 작업 목록 순서대로(Steam 계정 연결 → 게임 목록 → 병합 → 상세 채우기 → 출처 · 구매 정보 → 화면). 로컬 시험은 사용자의 실제 Steam 계정(게임 세부 정보 공개 필요) ⑤ M6.5 구매 기록 가져오기 ─ 시작할 때 사용자에게 Steam 구매 기록 · 라이선스 목록 페이지 복사본을 받아 형식부터 본다 ⑥ M6.7 비밀번호 변경 · 찾기 + 이메일 인증(새 단계, 메일 발송 서비스부터 정한다) ⑦ 12월 M5.5 서버 이사, M7 · M8, 그다음 확장 셋. 코드 · 문서는 Claude 자동, 서버 명령은 사용자가 친다. **Vultr 크레딧 2026-11-30 만료, 12월 AWS 이사** |
| 판단이 남은 것 | 모바일 첫 줄이 요약 줄 도착 때 24px 밀리는 것. S-05 방치 일수 색(180일 미만도 포인트 색). 개인정보 안내 문구(법률 검토 안 받음). 아이폰 확인. 비밀번호 보기 버튼을 Edge · 실제 폰에서 아직 안 봤다(운영에는 올라감). 백업 개인키 사본(`SERVER` 3.7절) |
| 기기별로 할 일 | **회사 PC · 노트북 공통**: `git pull` 뒤 `alembic upgrade head`(새 마이그레이션 `e4a48be57f0f` ─ `users.steam_synced_at`). 새 패키지는 없다. M6 코드를 시작하면 OpenID 콜백 시험에 로컬 API(`8001`) · 화면(`5173`)이 둘 다 떠 있어야 한다. **노트북**: 개발 환경 끝남(2026-11-06 (2), Task 3.54.0 있음). 서버 열쇠 · `venv.broken` 정리도 끝(2026-11-06 (10)). **서버 접속**: 세 기기 모두 된다(`ssh play`, 열쇠는 기기마다 따로). **전역 설정**(노트북 열쇠 반영): 집 PC는 원본 `~/.claude/CLAUDE.md`를 드라이브 사본 `desktop_hm_CLAUDE.md`로 맞춘다. 회사 PC는 드라이브 `.claude/README.md` "회사 PC에 올릴 것"을 반영한다 |
| 집 PC에만 있는 것 | 클린룸으로 새로 만든 개발 DB(확인용 계정 · 게임 기록). `.claude/launch.json`은 실행 중인 `5173`에 붙기만 하는 설정으로 새로 만들었다(커밋 안 함) |
| 회사 PC에만 있는 것 | **백업 개인키**(`~/playledger-backup.key`), 잠긴 운영 백업 8개(`~/playledger-backups/`, 11-06 받음). `.claude/worktrees/brave-hawking-fc3e7c`(병합됨, 지워도 된다). 헤드리스 Edge 확인 스크립트는 저장소에 없다 ─ 필요하면 [DEVLOG_M4.5](archive/DEVLOG_M4.5.md)를 보고 새로 만든다 |

## 작성 규칙

- 형식은 전역 설정 "문서 체계" 절을 따른다: `## YYYY-MM-DD (n) · 제목 (기기)` → 한 일 / `[설계]` / 막힌 것(증상 · 원인 · 해결 · 배운 것) / 이번 세션 커밋 / 다음에 할 일. 2026-11-02 이전 블록은 옛 형식 그대로 둔다
- 기기 표기는 `README` 개발 환경 표를 따른다 (데스크톱 A · 데스크톱 B · 노트북)
- **막혔던 점은 해결됐어도 반드시 남긴다.** 같은 실수를 반복하지 않기 위한 기록이고, 나중에 이 프로젝트를 설명할 때 "어떤 문제를 어떻게 해결했는가"가 결과물보다 더 중요한 이야기가 된다
- 환경 버전은 여기 적지 않는다. `requirements.txt` · `package.json` · `ci.yml`이 원본이고, 기기별 런타임은 `README`에 있다

---

## 2026-11-06 (11) · M6 Steam 계정 연결 ─ OpenID 시작 · 콜백 · 해제 (데스크톱 A, 마이그레이션까지 직접 · 그 뒤 자동)

### 한 일
- 사용자가 직접: `config.py` `public_base_url`, `models/user.py` `steam_synced_at`, 마이그레이션 `20261106_2012_add_steam_synced_at_to_users`(`e4a48be57f0f`). 관찰값: `alembic upgrade 8c2f4a71d9e3:head --sql` → `ALTER TABLE users ADD COLUMN steam_synced_at TIMESTAMP WITH TIME ZONE` 한 줄, `alembic current` → `e4a48be57f0f (head)`
- 자동: `core/oauth_state.py`(서명 state 쪽지, M8도 씀) · `services/steam_openid.py` · `routers/steam_link.py`(`POST /api/steam/link/start` · `GET /callback` · `DELETE /api/steam/link`), `UserRead`에 `steam_id` · `steam_synced_at`, 운영 `PUBLIC_BASE_URL`은 `deploy/compose.prod.yaml`에(비밀값이 아니라 서버 `.env`를 고칠 일이 없다)
- 테스트 `test_steam_link.py` 37개(위조 답 5 · Steam에 묻기 전에 거르는 망가진 확인서 13 · 값 개수, state 재사용 · 쿠키 없음 · 남의 콜백 · 만료 · 다른 용도 · 출입증으로 쓰기, `taken` · 409 · 두 탭 · 같은 Steam 동시 연결, Steam 장애 3, 해제 · 비로그인). `conftest` FakeSteam이 `steamcommunity.com`도 받는다
- 문서: `ARCHITECTURE` 5.4절 "구현하며 정한 것" 표, `PLAN` M6 첫 항목 · 진행 표, `server/.env.example`, `CLAUDE.md` `--sql` 범위

### [설계]
- 사전 검증에서 보완: 응답의 `openid.return_to`가 우리가 보낸 주소와 같은지도 본다 ─ Steam 서명은 "Steam이 썼다"까지만 보장하고, 다른 사이트용 확인서를 우리 콜백에 들이밀 수 있다
- 이미 Steam이 붙은 계정의 재연결은 막는다(시작 409, 두 탭은 `already`). 덮어쓰면 M6 병합에서 옛 Steam 기록과 섞인다
- 콜백은 페이지 이동이라 오류 JSON을 사람이 못 본다 ─ 결과를 `/settings?steam=`로 보낸다. 화면이 읽는 것은 S-06에서
- state 키를 access 토큰 키에서 갈라 냈다 ─ 같은 키면 `sub` · `exp`가 있는 state 쪽지가 출입증으로 통과한다

### 막힌 것
- **`alembic upgrade head --sql`이 `'NoneType' object has no attribute 'all'`로 멈춤** ─ 원인: 오프라인 모드는 DB를 보지 않아 맨 처음부터 SQL을 뽑고, 데이터를 읽는 `20261104_1420`에서 읽을 행이 없다. 해결: `이전리비전:head --sql`로 범위를 준다. `CLAUDE.md`를 고쳤다. 같은 시도에서 먼저 `ConnectionRefusedError [WinError 1225]`가 났는데 DB 컨테이너가 꺼져 있던 것
- **테스트가 엉뚱한 이유로 통과할 뻔함** ─ 쿠키를 `domain="test"`로 넣었는데 httpx는 `https://test`의 쿠키를 `test.local`로 담는다. 쿠키가 아예 안 실린 채 "실패"를 기대하는 테스트(재사용 · 만료)가 통과했다. `test.local`로 고친 뒤, 재사용 검사 줄을 일부러 꺼서 `test_state_cannot_be_reused`만 실패하는 것을 확인했다. 배운 것: 실패를 기대하는 테스트는 "막는 코드를 빼면 실패하는지"로 한 번 뒤집어 본다
- **실제 시험 중 재발급 동시 요청을 직접 밟음** ─ `/login` 화면을 연 채 스크립트로 `refresh`를 보내니 앱의 세션 복원 재발급과 겹쳐 재사용 감지가 시험 세션을 끊었다(`CLAUDE.md` 함정 그대로, 설계대로 동작). 화면이 없는 `/api/health` 페이지에서 새 시험 계정으로 다시 했다
- Steam은 로그인 뒤 "localhost에 로그인" 동의 화면을 한 번 더 보인다 ─ 첫 시도는 그 사이 state(5분)가 만료됐다. 화면 문구에 "5분 안에"를 넣을지는 S-06에서 본다

### 검증 (관찰값)
- `pytest` **352 passed**
- 로컬 실제 Steam(사용자 계정, `@example.com` 시험 계정 · 무작위 비밀번호): 가입 201 · 로그인 200 · start 200 → Steam이 `return_to=http://localhost:5173/...`를 받아 로그인 · 동의 화면 → 콜백 `303` → 개발 DB `users.steam_id`가 17자리로 저장, `steam_synced_at` NULL
- 같은 콜백 주소를 다시 보냄 → `303 /settings?steam=failed`. Steam에 같은 확인서를 다시 되물으면 Steam도 `is_valid:false`(Steam이 response_nonce를 한 번만 받는다)
- **확인 못 한 것**: 운영 배포 · 운영 도메인에서의 연결, 화면 버튼(S-06)

### 다음에 할 일
- M6 보유 게임 목록 조회(`GetOwnedGames`, 비공개 프로필 = 빈 응답 구분). 운영 배포는 S-06 화면이 붙은 뒤

---

## 2026-11-06 (10) · 노트북 `play-1` 열쇠, 비밀번호 찾기 단계 M6.7 (노트북, 서버 명령은 사용자)

### 한 일
- `SERVER` 3.1절 "다른 PC를 추가할 때": `play_vultr`(`-C laptop`, passphrase 있음) → Vultr 웹 콘솔에 root로 공개키 `>>` 추가 → `tail -n 3`에 `company-pc` · `home-pc` · `laptop` → `~/.ssh/config` `Host play`. 관찰값: `ssh -t play "sudo whoami"` → `root`, 접속 안내 디스크 35.1% · 메모리 39% · 스왑 0%. 기록은 `SERVER` 5절
- 노트북 `server/venv.broken` 지움(사용자)
- 전역 설정의 `play-1` 접속 기기 · 분실 대비 순서를 고침: 노트북 원본 · 사본, 집 PC 사본. 회사 PC는 드라이브 README "회사 PC에 올릴 것"
- 사용자가 "아이디 · 비밀번호 찾기가 없다"를 짚음 ─ 확인해 보니 비밀번호 찾기도, 로그인한 상태의 비밀번호 변경도 없다(`routers/auth.py`는 가입 · 로그인 · 재발급 · 로그아웃 · 계정 삭제뿐). 새 단계 **M6.7**: `REQUIREMENTS` F-39 변경 · F-40 찾기(새), F-27 이메일 인증 · F-29 모든 기기 로그아웃을 4.4절에서 4.3절로, `PLAN` M6.7 · 진행 표 · 버전 표 · 4장 그림, `README` 로드맵

### [설계]
- **범위를 일부러 넓힘**: 비밀번호를 잊으면 지금은 서버에서 직접 바꾸는 수밖에 없다. 남에게 보여 줄 서비스로는 빠지면 안 되는 기능이라 4.4절(있으면 좋은 것)이 아니라 단계로 잡았다
- 아이디 찾기는 따로 만들지 않는다 ─ 이메일이 곧 아이디이고, "그 이메일로 가입돼 있다"를 알려 주면 로그인 실패 문구를 하나로 묶은 원칙(`DESIGN` 3.1절 실패 메시지 원칙)이 깨진다
- 찾기(F-40)는 메일 발송 · 발신 도메인이 필요하고 F-27과 인프라가 같아서 묶었다. 변경(F-39)은 다른 기기 로그아웃이 F-29와 같은 쿼리라 같이
- 자리: M6 · M6.5 다음(사용자 선택). Steam 설계가 끝나 있어 흐름을 끊지 않는다. 메일 발송 서비스 · 기존 계정 인증 처리는 시작할 때 정한다(문서는 필요한 만큼만)

### 다음에 할 일
- "현재 상태" ④ M6 Steam 계정 연결 (자동 / 직접은 시작할 때 묻는다)

---

## 2026-11-06 (9) · Steam 게임의 구매일 · 구매가 보완 설계 (데스크톱 B, 자동 · 코드 없음)

### 한 일
- 사용자 질문 "Steam 연동이 끝나면 내 게임이 자동으로 붙나?"에 답하다가, Steam API가 **구매일 · 구매가를 주지 않는다**는 점을 사용자가 짚음 ─ 방치일수 · 시간당 비용이 이 앱의 정체성이다
- 출처를 따져 [decisions/0019](decisions/0019-steam-purchase-info.md): ① 첫 동기화 뒤 새 게임은 처음 본 날을 구매일로(동기화로 추정) ② 기존 라이브러리는 Steam 구매 기록 · 라이선스 목록 붙여넣기 가져오기 → **새 단계 M6.5** ③ 남은 빈칸은 S-10 구매 정보 채우기 화면. 모르는 값은 추정하지 않고 범위("N / M개 기준")를 보인다
- 사용자 선택: 가져오기는 M6.5로 뒤(형식을 실제 페이지로 먼저 확인), 스토어 정가 추정 버튼은 안 둠
- 문서: `REQUIREMENTS` F-37 · F-38, `DATA_MODEL` 2.6 "구매일 · 구매가의 출처"(구현 전), `DESIGN` 1장 S-10 · 3.2 `구매일 모름` · 3.5 범위 표시 · 3.9절(새), `PLAN` M6 작업 2개 · 완료 기준 2개, M6.5 단계(새) · 진행 표 · 버전 표

### [설계]
| 출처 | 구매일 | 구매가 | 쓰는 곳 |
|---|---|---|---|
| Steam Web API | ✗ | ✗ | ─ |
| 동기화가 처음 본 날 | ≈ 하루 오차 | ✗ | M6, 첫 동기화 뒤 새 게임만(첫 동기화 날을 넣으면 방치일수가 전부 0일이 된다) |
| Steam 구매 기록 페이지 | ✓ | ✓ 낸 돈 | M6.5 붙여넣기 |
| Steam 라이선스 목록 | ✓ 받은 날 | ✗ | M6.5 붙여넣기(키 · 번들도) |
| 스토어 현재 정가 | ✗ | 정가 | 쓰지 않음(세일가와 달라 시간당 비용이 부풀려짐) |
- 값마다 출처를 저장하고 사용자 입력이 늘 이긴다. "무료 · 번들이라 모름"은 사용자가 고른 값으로 남겨 빈칸과 구분
- Steam 비밀번호 · 로그인 쿠키를 받아 대신 긁지 않는다(계정 열쇠를 맡는 일, 약관)
- **확인 못 한 것**: 구매 기록 페이지의 실제 글 모양(날짜 · 원화 · 번들 · 환불 · 지갑 충전). M6.5 시작 때 사용자 복사본으로 본다

### 다음에 할 일
- "현재 상태" ⑤ M6 Steam 계정 연결부터 (자동 / 직접은 시작할 때 묻는다)

---

## 2026-11-06 (8) · Discord 로그인 사전 검증, 마일스톤 번호 다시 매기기 (데스크톱 B, 자동 · 코드는 주석만)

> 이 블록부터 새 번호다: M6 Steam 동기화 · M7 자동 동기화 · M8 Discord · M9 ~ M11 확장. 위 (7) 블록까지는 옛 번호([archive/README](archive/README.md) 대응표)

### 한 일
- 사용자 요청 ① Discord 로그인(옛 M11 → M8)도 M6처럼 사전 검증 ② Steam · Discord를 M5.5 다음으로 번호를 당기고 확장 기능은 뒤로, 순서 없이 병렬 가능하게
- [decisions/0017](decisions/0017-milestone-renumber.md)(0014 대체) · [0018](decisions/0018-discord-manual-link.md), `archive/README` 옛 번호 대응표, `PLAN` 표 · 단계 순서 · 버전 · 4장 그림 · M8 작업 목록 · 완료 기준, `ARCHITECTURE` 4.3 규칙 표 · 5.4, `DATA_MODEL` 2.1 · 2.3, `DESIGN` 3.1 · 3.6, `REQUIREMENTS` 3.1 · 4.3(버전 · 우선순위) · F-36 · R-07 · R-08, `README` 로드맵, 코드 주석 6곳(동작 변경 없음)

### [설계] Discord 사전 검증에서 발견
| # | 시나리오 | 원래 설계대로면 | 바꾼 것 |
|---|---|---|---|
| 1 | 이메일 자동 연결 | 가입 때 이메일 인증이 없어 남이 먼저 만든 계정에 내 Discord가 붙음(계정 선점) | 수동 연결만 (0018, 사용자가 장단점을 듣고 고름) |
| 2 | Discord 전용 계정 삭제 | 비밀번호가 없어 지울 수 없음 | `계정 삭제` 입력으로 확인 |
| 3 | Discord 전용 계정의 Discord 해제 | 로그인 수단이 없어짐 | 409, 비밀번호 추가는 F-36 |
| 4 | `state` 보관 | 정해지지 않음, `Strict` 쿠키는 외부에서 돌아오는 이동에 안 실림 | 서명 쿠키 `Lax` · 5분 · 한 번, Steam OpenID와 같은 모듈 |
| 5 | 콜백에서 refresh 쿠키 심기 | 브라우저마다 다를 수 있음(확정 못 함) | 구현 첫 단계에서 실제 브라우저로 확인, 안 되면 교환권 |
| 6 | 같은 Discord 두 탭 동시 첫 로그인 | 사용자 두 번 만들다 500 | UNIQUE에 걸리면 다시 조회 |
| 7 | 새 Discord 계정 이메일 = 기존 이메일 | `users.email` UNIQUE 충돌 | Discord 이메일을 받지 않음(`identify`만) |
| 8 | 동의 거절 · Discord 장애 | 규칙 없음 | 로그인 화면에 이유, 사용자 안 만듦 |
- 그대로 둔 것: 4.3절 흐름의 뼈대, `oauth_accounts`의 두 UNIQUE, client secret은 서버 `.env`만

### [설계] 번호
- Steam 수동 · 자동은 합치지 않았다(사용자 선택) ─ 수동은 그 자체로 배포할 수 있고, 자동은 Redis · 워커라 이사한 서버 사양을 보고 설계한다
- 버전: v1.1 배포(M5 · M5.5), v1.2 Steam(M6 · M7), v1.3 Discord(M8), 확장은 끝나는 순서대로 v1.4부터. 우선순위도 맞춰 F-12 · F-19 · F-21 → S, F-13 · F-14 · F-18 → L
- 확장 셋을 병렬로 하면 Alembic head가 갈린다 ─ `PLAN` 2장에 병합 마이그레이션을 적었다
- 지난 기록(archive · DEVLOG (7)까지 · 0014 ~ 0016)은 고치지 않고 대응표로. 목업 `.dc.html`도 캔버스 사본이라 그대로 둔다

### 막힌 것
- **번호 치환이 꼬였다.** 증상: `M6 → @@M9` 뒤에 같은 sed 안의 `\bM9\b` 규칙이 임시 표시까지 다시 바꿔 `@@@@M8` 같은 값이 나옴. 원인: `@`는 단어 문자가 아니라 `\b`가 그 앞에서도 걸린다. 해결: 커밋된 상태로 되돌리고 단어 경계에 안 걸리는 표시(`Mxq9`)로 다시 함. 배운 것: 여러 값을 한꺼번에 서로 바꿀 때 임시 표시는 원래 패턴에 다시 걸리지 않는 모양이어야 한다
- 서버에 깔린 `play-steam-sync.service`는 주석만 옛 번호다(동작 같음) ─ 다음에 그 파일을 고칠 때 같이 올린다

### 확인
- `npm run lint` exit 0, `format:check` 통과, `pytest tests/test_steam.py` 30 passed(주석 바뀐 파일)
- 남은 옛 번호 검색: 바뀐 11개 파일 diff를 줄마다 봤다. `v2.0` · `v2.1`은 DESIGN · DATA_MODEL · README · REQUIREMENTS에서 0

### 다음에 할 일
- M6 Steam 계정 연결부터. 시작 전에 자동 / 직접 칠지 묻고 OpenID 설명부터

---

## 2026-11-06 (7) · M8 Steam 동기화 설계 다시 잡기 (데스크톱 B, 자동 · 코드 없음)

### 한 일
- 사용자가 Steam · Discord 연동을 먼저 해 보고 싶어 했다 → 순서 M8 → M11 → M6 → M7 ([decisions/0014](decisions/0014-steam-discord-before-m6.md)). `PLAN` 4장에서 둘 다 점선(권장 순서)이라 막는 의존은 없었다
- 구현 전 사전 검증(사용자 요청: 지금 설계로 괜찮으면 그대로, 아니면 다시): `ARCHITECTURE` 5.1, `DATA_MODEL` 2.1 · 2.4 · 2.6, [decisions/0009](decisions/0009-manual-steam-separate.md), 지금 코드(`models/user.py` `steam_id` UNIQUE, `entries.source`, `services/steam.py`, 설정 화면의 자리만 있는 Steam 칸)를 시나리오로 따라감
- 결정 [0015](decisions/0015-steam-openid-link.md) · [0016](decisions/0016-steam-sync-details-later.md), `ARCHITECTURE` 5.1 규칙 표 · 5.4절(새), `DATA_MODEL` 2.1 · 2.4 · 2.6, `DESIGN` 3.4 · 3.6, `REQUIREMENTS` F-35, mockups README, `PLAN` M8 작업 목록 · 완료 기준

### [설계] 사전 검증에서 발견
| # | 시나리오 | 원래 설계대로면 | 바꾼 것 |
|---|---|---|---|
| 1 | 게임 500개 첫 동기화 | 새 게임마다 `appdetails` 500번 → 비공식 API 한도(대략 5분 200번)에 막힘 | `GetOwnedGames` 영어 이름으로 행만 만들고 상세는 나중에 조금씩 (0016) |
| 2 | 남의 Steam ID를 먼저 적기 | UNIQUE 때문에 진짜 주인이 연결 못 함 | Steam OpenID로 주인 확인 (0015) |
| 3 | 동기화 두 번 동시에 | 둘 다 "없음"을 보고 넣다 UNIQUE → 500 | 사용자별 잠금 + `ON CONFLICT`, 요청 제한 |
| 4 | 동기화로 들어온 게임의 상태 | 정해지지 않음 → 다 미시작이면 사장률이 엉망 | 0분 미시작 · 1분 이상 플레이중, 이후엔 안 바꿈 |
| 5 | Steam 검색으로 등록한 기록(`MANUAL`) | 영원히 건너뜀 | 상세 화면 "Steam에서 받기" 스위치 |
| 6 | 동기화된 기록의 플레이타임을 손으로 고침 | 다음 동기화가 덮어씀 | 고치면 `MANUAL` |
| 7 | 비공개 프로필 | 빈 응답이라 "추가 0"으로 보임 | `game_count` 없음 = 비공개, 409 + 안내 |
| 8 | Steam ID를 모름 | 17자리를 적어야 함 | 2와 같이 해결 |
| 9 | Steam에서 사라짐 · 플레이타임 줄어듦 | 규칙 없음 | 지우지 않음, Steam 값으로 맞추고 세션은 늘어난 만큼만 |
| 10 | 제목만 쳐서 만든 게임 + 같은 Steam 게임 | 두 줄(0009에서 감수) | 결과에 수를 알리고, 옮기기는 F-35로 미룸 |
- 처음 걱정한 "사용자의 사이버펑크 · RDR2가 두 줄이 된다"는 아니었다 ─ Steam 검색으로 골라 appid가 이미 붙어 있어서 동기화가 같은 기록으로 본다(5번 규칙으로 건너뜀)
- `source`는 게임 출처가 아니라 **플레이타임 출처**라는 것을 `DATA_MODEL` 2.6에 분명히 적었다(검색으로 등록한 기록도 `MANUAL`)
- 그대로 둔 것: `source` 규칙의 뼈대, 수동 · Steam 별개 행(0009), 구매가 · 평점 · 한줄평 보존, 첫 값은 기준점

### 다음에 할 일
- `PLAN` M8 "Steam 계정 연결"부터. 시작 전에 자동 / 직접 칠지 묻고, OpenID 개념 설명부터
- 새 패키지는 예상 없음(httpx로 된다)

---

## 끝난 단계

단계가 끝나면 날짜 블록을 [archive/](archive/README.md)로 옮기고 여기에는 한 줄만 남긴다.

| 단계 | 기간 | 한 줄 요약 | 블록 |
|---|---|---|---|
| M5 배포 | 2026-11-04 ~ 11-06 | `play.sagming.com` 첫 배포 · `task deploy` · HSTS 1년 · CSP · 감시(헬스 · 인증서 · 디스크) · 매일 백업 + R2 서버 밖 사본 · 복구 리허설 · `play-restore` · 재부팅 복구 · Steam 매주 타이머 · 운영 200개 최대 168ms · 닫기 전 점검(문서 15곳 고침), `pytest` 315건 · `npm test` 202건 | [DEVLOG_M5](archive/DEVLOG_M5.md) |
| M4.5 배포 전 정비 | 2026-11-04 | 서버 구멍 · 직접 등록 게임 분리 · 계정 삭제 · 탭 간 재발급 · 오류 처리 · CI 취약점 검사 · v1.0 독립 대조, `pytest` 310건 · `npm test` 202건 | [DEVLOG_M4.5](archive/DEVLOG_M4.5.md) |
| M4 통계 대시보드 | 2026-11-04 | 통계 API · S-05 화면 · 예시 데이터 · 손계산 대조, `npm audit` 정리 | [DEVLOG_M4](archive/DEVLOG_M4.md) |
| M3 상태 관리 + 평점 | 2026-11-03 ~ 11-04 | 상세 · 상태 · 평점 바로 고치기, 필터 · 주소 쿼리, 수정 · 삭제, 저장 알림, 수정 · 삭제 동시 실행 500 수정 | [DEVLOG_M3](archive/DEVLOG_M3.md) |
| M2 프론트 연동 · M2.5 Steam 검색 | 2026-09-28 ~ 11-03 | 로그인 · 목록 · 등록 · 설정 화면, 다크 · 라이트, Steam 검색 등록 · 커버, 상단 메뉴, ESLint · Prettier | [DEVLOG_M2](archive/DEVLOG_M2.md) |
| M1 백엔드 기초 | 2026-09-19 ~ 09-28 | 인증 · 보유 기록 CRUD · pytest 19건 · GitHub Actions · API 계약 문서 | [DEVLOG_M1](archive/DEVLOG_M1.md) |
| M0 환경 구성 | 2026-09-18 ~ 09-19 | 스택 전환 결정, Compose · FastAPI · Vue로 화면 → 서버 → DB 연결 | [DEVLOG_M0](archive/DEVLOG_M0.md) |
| v0 (옛 스택) | 2026-08-13 ~ 08-17 | RN + Django + MariaDB. 태그 `v0-rn-django` | [DEVLOG_v0](archive/DEVLOG_v0.md) |
