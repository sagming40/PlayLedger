// S-03 입력값을 SERVER가 받는 값으로 바꾸는 규칙 (DESIGN 3.3절)
// 화면과 떼어 둔다 ─ "1.5시간 → 90분" 같은 규칙을 화면 없이 테스트하기 위해서다

import type { Entry, EntryCreateBody, EntryStatus, EntryUpdateBody } from '@/api/entries'
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

// 수정 폼이 고칠 수 있는 칸 ─ 제목은 고칠 수 없다 (DATA_MODEL 2.6절)
// genreIds ─ 직접 등록한 게임은 지금 붙은 장르, Steam 게임은 새로 고른 장르만 담는다 (DATA_MODEL 2.5절)
export type EntryEditForm = Pick<EntryForm, 'status' | 'genreIds' | 'purchasedAt' | 'price' | 'hours' | 'rating' | 'review'>

/** 분 → 입력칸 글자. 90 → '1.5', 0 → '' (빈 칸 = 0시간, parseHours와 짝) */
function minutesToHours(minutes: number): string {
  if (minutes === 0) return ''
  // 소수 둘째 자리까지 ─ 100분은 '1.67'. 시간 칸은 분을 정확히 담지 못한다 (buildUpdateBody가 이 손실을 막는다)
  return String(Math.round((minutes / 60) * 100) / 100)
}

/** 저장된 기록 → 수정 폼의 처음 값 (DESIGN 3.3절 "기존 값 채워서 진입") */
export function entryToEditForm(entry: Entry): EntryEditForm {
  return {
    status: entry.status,
    genreIds: entry.game.steam_appid === null ? entry.game.genres.map((g) => g.id) : [],
    purchasedAt: entry.purchased_at ?? '',
    price: entry.purchase_price === null ? '' : String(entry.purchase_price),
    hours: minutesToHours(entry.playtime_minutes),
    rating: entry.rating,
    review: entry.review ?? '',
  }
}

/** 고른 순서는 뜻이 없다 ─ 눌렀다 뗀 뒤 다시 눌러도 바뀐 게 아니다 */
function sameIds(a: number[], b: number[]): boolean {
  return a.length === b.length && a.every((id) => b.includes(id))
}

/**
 * 수정 폼 → PATCH 본문. 잘못된 입력이 있으면 null, 바뀐 게 없으면 빈 객체
 *
 * **평점 보존 규칙 (DESIGN 4.3절)**: 평점 칸이 숨겨진 상태(클리어 · 포기가 아님)면 평점 · 한줄평을 아예 보내지 않는다
 * ─ buildCreateBody처럼 null을 보내면 CLEARED → PLAYING으로 바꿔 저장하는 순간 평점이 지워진다
 *
 * **손대지 않은 칸은 보내지 않는다**: 폼을 연 뒤 다른 기기 · 상세 화면에서 바꾼 값을 옛 값으로 덮어쓰지 않게 (PATCH = 보낸 항목만)
 * 비교는 저장된 값이 아니라 처음 채운 글자로 한다 ─ 100분은 '1.67'시간으로 보여서 다시 읽으면 100.2분이 된다
 */
export function buildUpdateBody(form: EntryEditForm, initial: EntryEditForm): EntryUpdateBody | null {
  const price = parsePrice(form.price)
  const minutes = parseHours(form.hours)
  if (price === undefined || minutes === undefined) return null

  const body: EntryUpdateBody = {}
  if (form.status !== initial.status) body.status = form.status
  if (!sameIds(form.genreIds, initial.genreIds)) body.genre_ids = form.genreIds
  if (form.purchasedAt !== initial.purchasedAt) body.purchased_at = form.purchasedAt || null
  if (form.price !== initial.price) body.purchase_price = price
  if (form.hours !== initial.hours) body.playtime_minutes = minutes

  if (canRate(form.status)) {
    if (form.rating !== initial.rating) body.rating = form.rating
    const review = form.review.trim()
    if (review !== initial.review.trim()) body.review = review || null
  }
  return body
}

const FIELD_LABEL: Record<string, string> = {
  email: '이메일',
  password: '비밀번호',
  nickname: '닉네임',
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
