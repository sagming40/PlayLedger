# PLAYLEDGER — DEVLOG

> **세션마다 겪은 일 · 막힌 일 · 배운 것**을 적는다. **최신이 위.** 지난 기록은 고치지 않고 위에 덧붙인다.
> 진행 상황 · 완료 기준은 [PLAN](PLAN.md), 결정의 이유는 [decisions/](decisions/README.md). 끝난 단계는 맨 아래 표에서 [archive/](archive/README.md)로.

## 현재 상태

| 항목 | 내용 |
|---|---|
| 단계 | **M5 ✅ 2026-11-06** (기록은 [DEVLOG_M5](archive/DEVLOG_M5.md), 닫기 전 점검 표는 그 파일 2026-11-06 (6)). 다음은 **M5.5 서버 이사**(12월, `PLAN`). `v1.0.0` 태그 있음. **`https://play.sagming.com` 운영 중**, 배포된 커밋 `c34b701` (`task deploy`) |
| 진행 중 | 없음. 운영 중인 것: 매일 백업(서버 14개 + R2 14일) · 디스크 감시(`/api/health` `disk`) · Steam 매주 타이머 · `uptime`. R2 14일 정리가 실제로 지우는 것은 11-20 이후에 처음 본다. `uptime` 예약 실행은 지금까지 3번(11-05 22:28 · 11-06 05:48 · 10:29 KST) ─ 30분마다인데 하루 몇 번만 돌아서 며칠 지켜본다 |
| 다음에 할 일 | ① 서버 열쇠: 노트북에서 `play_vultr`(`-C laptop`)를 만들고 공개키를 넣는다(`SERVER` 3.1절, 집 PC는 끝남). 사용자가 친다 ② `uptime` 실행 간격을 며칠 지켜본다, 새 "디스크 여유" 단계가 통과하는지 본다 ③ 11-08(일) 아침 `journalctl -u play-steam-sync`로 첫 예약 실행을 본다 ④ 11-20 이후 R2 버킷에서 14일 지난 사본이 지워졌는지 본다(`SERVER` 5절 맨 아래) ⑤ 12월 M5.5 서버 이사(`PLAN`), 그다음 M6. 코드 · 문서는 Claude 자동, 서버 명령은 사용자가 친다. **Vultr 크레딧 2026-11-30 만료, 12월 AWS 이사** |
| 판단이 남은 것 | 모바일 첫 줄이 요약 줄 도착 때 24px 밀리는 것. S-05 방치 일수 색(180일 미만도 포인트 색). 개인정보 안내 문구(법률 검토 안 받음). 아이폰 확인. 비밀번호 보기 버튼을 Edge · 실제 폰에서 아직 안 봤다(운영에는 올라감). 백업 개인키 사본(`SERVER` 3.7절) |
| 기기별로 할 일 | **집 PC · 노트북 공통**: `git pull`. 새 패키지 · 마이그레이션은 없다. **노트북**: 개발 환경 끝남(2026-11-06 (2), Task 3.54.0 있음). 남은 것은 서버 열쇠(위 ①) → `server/venv.broken` 지우기. **서버 접속**: 회사 PC · 집 PC는 된다. 노트북은 아직 |
| 집 PC에만 있는 것 | `play-1` SSH 열쇠(`~/.ssh/play_vultr`, 회사 PC 것과 별개). 클린룸으로 새로 만든 개발 DB(확인용 계정 · 게임 기록). `.claude/launch.json`은 실행 중인 `5173`에 붙기만 하는 설정으로 새로 만들었다(커밋 안 함) |
| 회사 PC에만 있는 것 | **백업 개인키**(`~/playledger-backup.key`), 잠긴 운영 백업 8개(`~/playledger-backups/`, 11-06 받음). `.claude/worktrees/brave-hawking-fc3e7c`(병합됨, 지워도 된다). 헤드리스 Edge 확인 스크립트는 저장소에 없다 ─ 필요하면 [DEVLOG_M4.5](archive/DEVLOG_M4.5.md)를 보고 새로 만든다 |

## 작성 규칙

- 형식은 전역 설정 "문서 체계" 절을 따른다: `## YYYY-MM-DD (n) · 제목 (기기)` → 한 일 / `[설계]` / 막힌 것(증상 · 원인 · 해결 · 배운 것) / 이번 세션 커밋 / 다음에 할 일. 2026-11-02 이전 블록은 옛 형식 그대로 둔다
- 기기 표기는 `README` 개발 환경 표를 따른다 (데스크톱 A · 데스크톱 B · 노트북)
- **막혔던 점은 해결됐어도 반드시 남긴다.** 같은 실수를 반복하지 않기 위한 기록이고, 나중에 이 프로젝트를 설명할 때 "어떤 문제를 어떻게 해결했는가"가 결과물보다 더 중요한 이야기가 된다
- 환경 버전은 여기 적지 않는다. `requirements.txt` · `package.json` · `ci.yml`이 원본이고, 기기별 런타임은 `README`에 있다

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
