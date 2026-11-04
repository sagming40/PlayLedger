# archive — 옛 문서 보관함

> **지금은 쓰지 않지만 남겨 두는 문서**를 모은 폴더다. 보관만 하고 고치지 않는다.
> 지금 문서는 [CLAUDE.md](../../CLAUDE.md) "문서 지도", 진행 상황은 [PLAN](../PLAN.md).

## 개발 일지 — 끝난 단계

마일스톤이 끝나면 그 기간의 [DEVLOG](../DEVLOG.md) 날짜 블록을 여기로 옮긴다. 줄을 그대로 옮기고 머리말만 붙였다.

| 파일 | 단계 | 기간 |
|---|---|---|
| [DEVLOG_M0.md](DEVLOG_M0.md) | M0 환경 구성 (스택 전환 결정 포함) | 2026-09-18 ~ 09-19 |
| [DEVLOG_M1.md](DEVLOG_M1.md) | M1 백엔드 기초 | 2026-09-19 ~ 09-28 |
| [DEVLOG_M2.md](DEVLOG_M2.md) | M2 프론트 연동 · M2.5 Steam 검색 | 2026-09-28 ~ 11-03 |
| [DEVLOG_M3.md](DEVLOG_M3.md) | M3 상태 관리 + 평점 | 2026-11-03 ~ 11-04 |
| [DEVLOG_v0.md](DEVLOG_v0.md) | 스택 전환 전 v0 (M 번호가 지금과 겹쳐 따로 둔다) | 2026-08-13 ~ 08-17 |

v0 코드와 그때 문서는 git 태그 `v0-rn-django`에서 볼 수 있다.

## 옛 문서 이름 대응표

옛 기록은 고치지 않으므로 당시 이름이 그대로 남아 있다. 2026-11-02에 문서를 재정비하면서 이름이 바뀌었다 ([decisions/0001](../decisions/0001-docs-refactor.md)).

| 옛 이름 | 옛 파일 | 지금 |
|---|---|---|
| `REQUIREMENTS` | `01_requirements.md` | [REQUIREMENTS](../REQUIREMENTS.md) (1 ~ 5장 번호 그대로. 6장 → DATA_MODEL, 7 · 8장 → 6 · 7장, 9장 → PLAN, 10장 → decisions · PLAN) |
| `ARCHITECTURE` | `02_architecture.md` | [ARCHITECTURE](../ARCHITECTURE.md) (4 ~ 8장 번호 그대로. 3장 기술 선택 근거 → [decisions/0002](../decisions/0002-stack-switch.md)) |
| `ERD` | `03_erd.md` (더 옛날엔 `ERD.md`) | [DATA_MODEL](../DATA_MODEL.md) (절 번호 그대로) |
| `UI_DESIGN` | `04_ui_design.md` | [DESIGN](../DESIGN.md) (절 번호 그대로) |
| `MILESTONES` | `05_milestones.md` | [PLAN](../PLAN.md) |
| `API_SPEC` | `06_api_spec.md` | [ARCHITECTURE](../ARCHITECTURE.md) 3장 (아래 표) |

| `API_SPEC` | `ARCHITECTURE` |
|---|---|
| 2장 (2.1 ~ 2.3) | 3.1 |
| 3.1 / 3.2 / 3.3 / 3.4 | 3.2 / 3.3 / 3.4 / 3.5 |
| 4.1 / 4.2 / 4.3 / 4.4 / 4.5 | 3.6 / 3.7 / 3.8 / 3.9 / 3.10 |

재정비 직전 문서 전체는 커밋 `122be62`에서 볼 수 있다.

## 문서 부속

| 파일 | 내용 |
|---|---|
| [CHANGELOG_old_docs.md](CHANGELOG_old_docs.md) | 재정비 전 문서 끝에 있던 변경 이력 표. 이제 변경 이력은 git이 원본이고 이유는 `decisions/` · DEVLOG `[설계]`에 적는다 |
| [MILESTONES_M0_M1.md](MILESTONES_M0_M1.md) | 끝난 M0 · M1의 작업 목록 · 완료 기준 체크리스트와 각주 |
