import { request } from './client'
import type { Genre } from './entries'

// GET /api/genres ─ 고정 목록 (DATA_MODEL 2.5절). id는 기기마다 다르므로 숫자로 가정하지 않는다
export function listGenres() {
  return request<Genre[]>('/genres')
}
