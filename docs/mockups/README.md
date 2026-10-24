# mockups — 화면 목업 원본

claude.ai 디자인 캔버스("PlayLedger 목업")의 원본 파일을 옮겨 둔 폴더다.
캔버스는 개인 계정 소유라 다른 계정에서는 열리지 않아서, 어느 계정 · 어느 기기에서든 볼 수 있게 저장소에 둔다.

- 캔버스(개인 계정): https://claude.ai/artifact/U1ZEc9PdpwdczuJcADR9ro
- 화면 규격과 색 결정은 [`../04_ui_design.md`](../04_ui_design.md)가 단일 출처다 (색 · 테마는 4.4절). 이 폴더는 그 결정을 그림으로 보여 주는 참고 자료다
- 2026-10-24 기준 사본이다. 캔버스를 고치면 이 폴더도 다시 옮겨야 같아진다

## 확정된 것 (2026-10-24)
- 컬러 시안 **A · 심야 극장** — 포인트 `#D12E34` 하나 + 무채색
- 상태 5색은 **현행안**(`UI_DESIGN` 4.1절) — 플레이중 파랑 · 클리어 초록 · 포기 흐린 회색
- 테마는 **다크 · 라이트 둘 다** (F-24를 v1.0으로 앞당김). 기본은 시스템 설정을 따른다

## 보는 방법
- 파일 하나가 보드 하나다. 브라우저로 열면 대략적인 모양은 보인다 (캔버스 전용 스크립트 `support.js`가 없어서 그대로는 렌더링되지 않을 수 있음)
- 화면 보드는 캔버스의 Tweaks에서 다크 / 라이트, 팔레트, 상태색을 바꿔 볼 수 있다. 기본값이 확정안이다
- `canvas.json`은 캔버스 목차다. 보드 이름(`title`)과 위치가 들어 있다
- 게임 커버 자리는 실제 이미지 대신 단색 블록이다 (커버는 M2.5 이후). 숫자는 `UI_DESIGN` 와이어프레임의 예시 값이다

## 파일

| 보드 | 파일 |
|---|---|
| 컬러 시안 A~D · 다크 / 라이트 | `Main.dc.html` |
| 상태 5색 · 현행안 vs 교체안 | `StatusColors.dc.html` |
| S-01 로그인 · 가입 (전환 동작) | `Login.dc.html` |
| S-02 라이브러리 · 데스크톱 / 모바일 / 빈 상태 | `Library.dc.html`, `LibraryMobile.dc.html`, `LibraryEmpty.dc.html` |
| S-03 게임 등록 (상태에 따라 평점 칸) | `Form.dc.html` |
| S-04 게임 상세 · 데스크톱 / 모바일 / 삭제 확인 | `Detail.dc.html`, `DetailMobile.dc.html`, `DeleteDialog.dc.html` |
| S-05 통계 · 데스크톱 / 모바일 | `Stats.dc.html`, `StatsMobile.dc.html` |
| S-06 설정 | `Settings.dc.html` |

S-07(다음 게임 추첨, v1.1)은 그리지 않았다.
