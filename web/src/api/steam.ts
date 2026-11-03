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
