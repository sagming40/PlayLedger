# mockups — 화면 목업

> **화면 결정을 그림으로 보여 주는 참고 자료**다. 화면 규격과 색의 단일 출처는 [DESIGN](../DESIGN.md)이다 (색 · 테마는 4.4절).
> 원본은 claude.ai 디자인 캔버스("PlayLedger 목업")이고, 2026-10-24 기준 사본을 옮겨 두었다. 캔버스는 개인 계정 소유라 다른 계정에서는 열리지 않아서, 어느 계정 · 어느 기기에서든 볼 수 있게 저장소에 둔다.

- 캔버스(개인 계정): https://claude.ai/artifact/U1ZEc9PdpwdczuJcADR9ro
- 캔버스를 고치면 이 폴더도 다시 옮겨야 같아진다

## 확정된 것 (2026-10-24)
- 컬러 시안 **A · 심야 극장** — 포인트 `#D12E34` 하나 + 무채색
- 상태 5색은 **현행안**(`DESIGN` 4.1절) — 플레이중 파랑 · 클리어 초록 · 포기 흐린 회색
- 테마는 **다크 · 라이트 둘 다** (F-24를 v1.0으로 앞당김). 기본은 시스템 설정을 따른다

## 보는 방법
- 파일 하나가 보드 하나다. `.dc.html`을 브라우저로 그냥 열면(더블클릭) 캔버스와 같은 모양으로 나온다. 앱 내장 브라우저는 로컬 파일에서 스크립트가 돌지 않아 로컬 서버(`python -m http.server`)가 필요하다
  - 같은 폴더의 `support.js`가 `{{ }}` 빈칸 · `<sc-for>` · `<sc-if>`를 풀어서 그린다. 캔버스 런타임을 이 폴더의 목업이 쓰는 만큼만 흉내 낸 로컬 미리보기용 파일이다 (캔버스에는 올리지 않는다)
  - 주소 뒤에 값을 붙이면 기본값 대신 그 값으로 그린다: `Library.dc.html?dark=false` (라이트), `?palette=C 장부 앰버`, `?statusScheme=교체안`
  - S-01 · S-03은 클릭하면 동작한다 (가입 전환, 상태에 따라 평점 칸)
- 캔버스에서는 Tweaks로 같은 값을 바꿔 볼 수 있다. 기본값이 확정안이다
- VS Code는 이 폴더의 `.dc.html`을 handlebars로 읽는다 (`.vscode/settings.json`). HTML로 읽으면 `{{ }}`를 CSS 오류로 잘못 잡는다
- `canvas.json`은 캔버스 목차다. 보드 이름(`title`)과 위치가 들어 있다
- 게임 커버 자리는 실제 이미지 대신 단색 블록이다 (커버는 M2.5 이후). 숫자와 제목은 지어낸 예시 값이다

**파일 이름은 전역 문서 체계와 다르게 둔다** — `화면.기기.html`이 아니라 `화면.dc.html` · `화면Mobile.dc.html`이다. 캔버스 원본의 사본이라 이름을 바꾸면 링크 · import 33곳과 `support.js` · `canvas.json`을 같이 고쳐야 하고, 캔버스에서 다시 옮겨 올 때 어긋날 수 있다 ([decisions/0001](../decisions/0001-docs-refactor.md)).

## 파일

| 보드 | 파일 | DESIGN | 상태 |
|---|---|---|---|
| 컬러 시안 A~D · 다크 / 라이트 | `Main.dc.html` | 4.4절 | **A 채택** (2026-10-24), B · C · D는 비교용 |
| 상태 5색 · 현행안 vs 교체안 | `StatusColors.dc.html` | 4.1절 | **현행안 채택** (2026-10-24), 교체안은 비교용 |
| S-01 로그인 · 가입 (전환 동작) | `Login.dc.html` | 3.1절 | 채택 (2026-10-24). 배경 타일 수는 옛 안 — 구현이 기준 |
| S-02 라이브러리 · 데스크톱 / 모바일 / 빈 상태 | `Library.dc.html`, `LibraryMobile.dc.html`, `LibraryEmpty.dc.html` | 3.2 · 5장 | 채택 (2026-10-24) |
| S-03 게임 등록 (상태에 따라 평점 칸) | `Form.dc.html` | 3.3절 | 채택 (2026-10-24), 구현됨 |
| S-04 게임 상세 · 데스크톱 / 모바일 / 삭제 확인 | `Detail.dc.html`, `DetailMobile.dc.html`, `DeleteDialog.dc.html` | 3.4절 | 채택 (2026-10-24). 구현됨 |
| S-05 통계 · 데스크톱 / 모바일 | `Stats.dc.html`, `StatsMobile.dc.html` | 3.5절 | 채택 (2026-10-24), 구현됨. 장르별 완주율은 그림의 CSS 막대가 아니라 ECharts ─ 구현이 기준 |
| S-06 설정 | `Settings.dc.html` | 3.6절 | 채택 (2026-10-24). 계정 삭제 · 개인정보 안내 링크는 그림에 없다 ─ 구현이 기준 |
| 상단 메뉴 시안 A ~ H 비교 (D ~ H는 B 기반) | `TopNavBoard.dc.html`, `TopNav.dc.html` (`?variant=A` · `?screen=plain` · `?dark=false`) | 2.2절 | **H 채택** (2026-11-03, E + G의 아이콘). **F(떠 있는 캡슐)는 나중에 다시 볼 후보**, 나머지는 비교용. 캔버스 없이 저장소에서 직접 그렸다. material-dict 추천안의 상단 메뉴를 참고 |

`Library`에 없는 장르 칸은 구현이 기준이다(정렬 칸 옆). `Form`의 구매일 칸 · `Detail`의 상태 칸도 shadcn 부품으로 구현했다(`DESIGN` 3.3 · 3.4절). `Library`의 요약 줄 `가장 오래 방치`는 옛 안 — 구현이 기준이다. 통계 화면에 같은 내용이 있어 넣지 않았다.

데스크톱 보드(`Library` · `LibraryEmpty` · `Form` · `Detail` · `Stats` · `Settings`)의 왼쪽 사이드바는 옛 안이다 — 메뉴는 `TopNav.dc.html` 시안 H가 기준이다.

S-07(다음 게임 추첨, v1.1) · S-08(위시리스트, v1.2)은 그리지 않았다. `DESIGN` 3.7 · 3.8절의 와이어프레임을 본다. S-09(개인정보 안내, M4.5)도 그리지 않았다 ─ 글만 있는 화면이라 구현(`web/src/views/PrivacyView.vue`)이 기준이다.
