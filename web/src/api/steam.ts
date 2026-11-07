import { request } from './client'

// 검색 후보 하나 (server/app/schemas/steam.py). 이름은 미러의 영어 이름이다 (decisions/0008)
export interface SteamApp {
  appid: number
  name: string
}

// GET /api/steam/apps ─ encodeURIComponent를 빼면 'R&D' 같은 제목에서 & 뒤가 잘린다
export function searchSteamApps(query: string) {
  return request<SteamApp[]>(`/steam/apps?q=${encodeURIComponent(query)}`)
}

// ─── Steam 계정 연결 · 동기화 (DESIGN 3.6절, ARCHITECTURE 5.1 · 5.4절) ───

// POST /api/steam/link/start ─ 페이지 이동이 아니라 fetch다. access 토큰이 메모리에만 있어 페이지 이동에는 실리지 않는다
// 돌려받은 주소로 화면이 직접 이동한다
export function startSteamLink() {
  return request<{ redirect_url: string }>('/steam/link/start', { method: 'POST' })
}

// DELETE /api/steam/link ─ 가져온 기록은 남는다. 이미 풀려 있어도 204
export function unlinkSteam() {
  return request<void>('/steam/link', { method: 'DELETE' })
}

// 동기화 결과 (server/app/schemas/steam.py SteamSyncRead)
export interface SteamSyncResult {
  added: number
  updated: number
  unchanged: number
  skipped_manual: number // 직접 입력한 기록이라 그대로 둠
  skipped_limit: number // 기록 상한(5,000개)을 넘어 넣지 못함
  skipped_no_title: number // 이름을 쓸 수 없어 건너뜀
  same_title_manual: number // 새 Steam 기록 중 직접 등록한 게임과 제목이 같은 것
  synced_at: string
  steam_persona_name: string | null
}

// POST /api/steam/sync ─ 409 미연결 · 비공개, 429 너무 잦음, 502 · 504 Steam 장애
export function syncSteam() {
  return request<SteamSyncResult>('/steam/sync', { method: 'POST' })
}
