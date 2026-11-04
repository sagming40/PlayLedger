import { request } from './client'

// SERVER 응답 모양 (server/app/schemas/stats.py)

export interface IdleGame {
  entry_id: number
  title: string
  cover_url: string | null
  idle_days: number
}

export interface CostlyGame {
  entry_id: number
  title: string
  cover_url: string | null
  cost_per_hour: number // 원/시간
}

export interface GenreStat {
  genre_id: number
  name: string
  total: number
  started: number // 미시작을 뺀 수 ─ 완주율의 분모
  cleared: number
  completion_rate: number | null // %. 시작한 게임이 없으면 null (0%와 다르다)
  avg_playtime_minutes: number | null // 시작한 게임의 평균
}

export interface Stats {
  total: number
  backlog: number
  abandoned_rate: number | null // 사장률 %
  completion_rate: number | null // 완주율 %
  longest_idle: IdleGame[]
  highest_cost: CostlyGame[]
  genres: GenreStat[]
}

// GET /api/stats ─ today는 브라우저의 오늘. 방치일수를 목록 카드와 같은 날짜로 센다
export function getStats(today: string) {
  return request<Stats>(`/stats?today=${today}`)
}
