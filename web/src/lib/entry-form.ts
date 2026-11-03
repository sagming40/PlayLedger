// S-03 입력값을 SERVER가 받는 값으로 바꾸는 규칙 (DESIGN 3.3절)
// 화면과 떼어 둔다 ─ "1.5시간 → 90분" 같은 규칙을 화면 없이 테스트하기 위해서다

import type { EntryCreateBody, EntryStatus } from '@/api/entries'
import type { FieldIssue } from '@/api/errors'
import type { SteamApp } from '@/api/steam'

// PostgreSQL integer 최댓값 ─ 서버 schemas/entry.py의 INT_MAX와 같다
const INT_MAX = 2_147_483_647

export const STATUSES: EntryStatus[] = ['BACKLOG', 'PLAYING', 'CLEARED', 'ON_HOLD', 'DROPPED']

/** 평점 · 한줄평은 끝난 게임에만 적는다 (DESIGN 3.3절) */
export function canRate(status: EntryStatus): boolean {
  return status === 'CLEARED' || status === 'DROPPED'
}

/** '66,000' → 66000. 빈 칸은 null(모름), 숫자가 아니면 undefined(잘못된 입력) */
export function parsePrice(text: string): number | null | undefined {
  const t = text.replace(/[,\s]/g, '')
  if (t === '') return null
  if (!/^\d+$/.test(t)) return undefined
  const n = Number(t)
  return n <= INT_MAX ? n : undefined
}

/** 시간 → 분 (DESIGN 3.3절). '1.5' → 90. 빈 칸은 0, 숫자가 아니면 undefined */
export function parseHours(text: string): number | undefined {
  const t = text.trim()
  if (t === '') return 0
  if (!/^\d+(\.\d+)?$/.test(t)) return undefined
  const minutes = Math.round(Number(t) * 60)
  return minutes <= INT_MAX ? minutes : undefined
}

export interface EntryForm {
  title: string
  steamApp: SteamApp | null
  status: EntryStatus
  genreIds: number[]
  purchasedAt: string
  price: string
  hours: string
  rating: number | null
  review: string
}

/**
 * 폼을 요청 본문으로 바꾼다. 잘못된 입력이 있으면 null
 *
 * Steam 게임은 제목을 보내지 않는다 ─ 제목은 SERVER가 찾는다 (ARCHITECTURE 5.3절)
 * 상태를 바꿔 숨겨진 평점 칸의 값은 보내지 않는다 ─ 안 보이는 값이 저장되면 안 된다
 */
export function buildCreateBody(form: EntryForm): EntryCreateBody | null {
  const price = parsePrice(form.price)
  const minutes = parseHours(form.hours)
  if (price === undefined || minutes === undefined) return null

  const rated = canRate(form.status)
  const review = form.review.trim()
  const common = {
    status: form.status,
    genre_ids: form.genreIds,
    purchased_at: form.purchasedAt || null,
    purchase_price: price,
    playtime_minutes: minutes,
    rating: rated ? form.rating : null,
    review: rated && review ? review : null,
  }

  if (form.steamApp) return { steam_appid: form.steamApp.appid, ...common }
  const title = form.title.trim()
  if (!title) return null
  return { title, ...common }
}

const FIELD_LABEL: Record<string, string> = {
  title: '제목',
  purchased_at: '구매일',
  purchase_price: '구매가',
  playtime_minutes: '플레이타임',
  rating: '평점',
  review: '한줄평',
}

/** Pydantic 422의 issues → 화면 문구. msg는 영문이라 쓰지 않는다 (ARCHITECTURE 3.9절) */
export function issuesMessage(issues: FieldIssue[]): string | null {
  const labels = [...new Set(issues.map((i) => FIELD_LABEL[i.field]).filter(Boolean))]
  return labels.length ? `${labels.join(' · ')}을(를) 다시 확인해 주세요` : null
}
