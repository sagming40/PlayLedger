import { request } from './client'

// SERVER 응답 모양 (server/app/schemas/entry.py · game.py · genre.py)
// 모양은 Swagger의 실제 응답과 대조할 것 ─ 모자란 필드는 타입 검사가 잡지 못한다 (DEVLOG 09-29)

export type EntryStatus = 'BACKLOG' | 'PLAYING' | 'CLEARED' | 'ON_HOLD' | 'DROPPED'

export interface Genre {
  id: number
  name: string
}

export interface Game {
  id: number
  title: string
  genres: Genre[]
}

export interface Entry {
  id: number
  game: Game
  status: EntryStatus
  purchased_at: string | null // 날짜 'YYYY-MM-DD' ─ 시각 파서로 읽으면 하루가 어긋난다
  purchase_price: number | null // 원
  playtime_minutes: number // 분
  rating: number | null
  review: string | null
  source: 'MANUAL' | 'STEAM'
  created_at: string // UTC 시각 '...Z'
  updated_at: string
}

export interface EntryListResponse {
  items: Entry[]
  total: number // 조건에 맞는 전체 개수 ─ items는 이번 페이지만
}

export interface ListParams {
  status?: EntryStatus
  limit?: number
  offset?: number
}

// GET /api/entries ─ 최근 수정순 (UI_DESIGN 3.2절 정렬 기본값, SERVER가 정렬한다)
export function listEntries(params: ListParams = {}) {
  const query = new URLSearchParams()
  if (params.status) query.set('status', params.status)
  if (params.limit !== undefined) query.set('limit', String(params.limit))
  if (params.offset !== undefined) query.set('offset', String(params.offset))
  const qs = query.toString()
  return request<EntryListResponse>(`/entries${qs ? `?${qs}` : ''}`)
}
