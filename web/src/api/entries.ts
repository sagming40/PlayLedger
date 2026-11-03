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
  steam_appid: number | null // 수동 등록 게임은 없다
  cover_url: string | null // 없거나 깨지면 제목 앞 두 글자로 대체한다 (DESIGN 4.4절)
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

// title과 steam_appid 중 정확히 하나만 보낸다 (ARCHITECTURE 5.3절)
export interface EntryCreateBody {
  title?: string
  steam_appid?: number
  status: EntryStatus
  genre_ids: number[]
  purchased_at: string | null
  purchase_price: number | null
  playtime_minutes: number
  rating: number | null
  review: string | null
}

// POST /api/entries ─ 201. 이미 내 라이브러리에 있으면 409
export function createEntry(body: EntryCreateBody) {
  return request<Entry>('/entries', { method: 'POST', body })
}

// GET /api/entries ─ 최근 수정순 (DESIGN 3.2절 정렬 기본값, SERVER가 정렬한다)
export function listEntries(params: ListParams = {}) {
  const query = new URLSearchParams()
  if (params.status) query.set('status', params.status)
  if (params.limit !== undefined) query.set('limit', String(params.limit))
  if (params.offset !== undefined) query.set('offset', String(params.offset))
  const qs = query.toString()
  return request<EntryListResponse>(`/entries${qs ? `?${qs}` : ''}`)
}
