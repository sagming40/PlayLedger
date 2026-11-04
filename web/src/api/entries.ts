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
  cost_per_hour: number | null // 원/시간, SERVER 계산값. 플레이타임 0 · 구매가 없음이면 null (REQUIREMENTS 5.1절)
  created_at: string // UTC 시각 '...Z'
  updated_at: string
}

export interface EntryListResponse {
  items: Entry[]
  total: number // 조건에 맞는 전체 개수 ─ items는 이번 페이지만
}

export type EntrySort = 'updated' | 'purchased' | 'title' | 'playtime'

export interface ListParams {
  status?: EntryStatus
  genre?: number
  sort?: EntrySort
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

// GET /api/entries ─ 정렬 · 필터는 SERVER가 한다. 정렬 기본값은 최근 수정순 (DESIGN 3.2절)
export function listEntries(params: ListParams = {}) {
  const query = new URLSearchParams()
  if (params.status) query.set('status', params.status)
  if (params.genre !== undefined) query.set('genre', String(params.genre))
  if (params.sort) query.set('sort', params.sort)
  if (params.limit !== undefined) query.set('limit', String(params.limit))
  if (params.offset !== undefined) query.set('offset', String(params.offset))
  const qs = query.toString()
  return request<EntryListResponse>(`/entries${qs ? `?${qs}` : ''}`)
}

// GET /api/entries/:id ─ S-04 상세. 없거나 남의 기록이면 404 (ARCHITECTURE 3.8절)
export function getEntry(id: number) {
  return request<Entry>(`/entries/${id}`)
}

// 수정 요청 ─ 보낸 항목만 바뀐다. 제목은 받지 않는다 (DATA_MODEL 2.6절)
export type EntryUpdateBody = Partial<Omit<EntryCreateBody, 'title' | 'steam_appid'>>

// PATCH /api/entries/:id ─ 상세 화면의 상태 변경은 { status }만 보낸다 (DESIGN 3.4절)
export function updateEntry(id: number, body: EntryUpdateBody) {
  return request<Entry>(`/entries/${id}`, { method: 'PATCH', body })
}

// DELETE /api/entries/:id ─ 204. Steam 게임은 다른 사람도 쓰므로 남고, 직접 등록한 게임은 함께 지워진다
export function deleteEntry(id: number) {
  return request<void>(`/entries/${id}`, { method: 'DELETE' })
}
