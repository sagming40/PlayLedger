// 보유 기록을 화면에 보일 글자로 바꾸는 규칙 (DESIGN 3.2 · 4.1 · 4.2절)
// 계산은 SERVER가 하는 것이 원칙이지만(S-05), 목록 카드의 방치일수 · 시간 표기는 화면 표시 변환이라 여기서 한다

import type { Entry, EntryStatus } from '@/api/entries'

export const STATUS_LABEL: Record<EntryStatus, string> = {
  BACKLOG: '미시작',
  PLAYING: '플레이중',
  CLEARED: '클리어',
  ON_HOLD: '보류',
  DROPPED: '포기',
}

// 상태 점의 색 ─ style.css의 상태 토큰을 쓰는 Tailwind 클래스 (색만으로 구분하지 않고 글자와 함께 쓴다)
export const STATUS_DOT_CLASS: Record<EntryStatus, string> = {
  BACKLOG: 'bg-status-backlog',
  PLAYING: 'bg-status-playing',
  CLEARED: 'bg-status-cleared',
  ON_HOLD: 'bg-status-on-hold',
  DROPPED: 'bg-status-dropped',
}

/**
 * 'YYYY-MM-DD'를 그 지역의 그날 0시로 읽는다
 *
 * new Date('2026-10-25')는 UTC 0시로 해석되어, 한국에서는 10/25 09:00이 된다.
 * 날짜끼리 빼면 시차만큼 어긋나므로 연 · 월 · 일을 직접 꺼내 만든다 (CLAUDE.md 함정 "날짜와 시각")
 */
function parseLocalDate(ymd: string): Date | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(ymd)
  if (!m) return null
  return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]))
}

/**
 * 방치일수 = 구매일로부터 오늘까지의 일수 (REQUIREMENTS 2장 용어 정의)
 * 구매일이 없으면 계산할 수 없다 → null. 미래 날짜(입력 실수)는 0으로 본다
 */
export function idleDays(purchasedAt: string | null, today: Date = new Date()): number | null {
  if (!purchasedAt) return null
  const bought = parseLocalDate(purchasedAt)
  if (!bought) return null
  const start = new Date(today.getFullYear(), today.getMonth(), today.getDate())
  // 하루 = 86,400,000ms. 서머타임이 없는 한국 기준이지만 반올림으로 1시간 차이도 흡수한다
  const days = Math.round((start.getTime() - bought.getTime()) / 86_400_000)
  return Math.max(0, days)
}

/** 분 → '12.5시간'. SERVER는 분으로 주고 화면은 시간(소수 한 자리)으로 보여준다 (DESIGN 3.2절) */
export function formatPlaytime(minutes: number): string {
  return `${(minutes / 60).toFixed(1)}시간`
}

export interface CardMetric {
  text: string | null // 상태 뒤에 붙는 글자. 없으면 상태만 보인다
  loud: boolean // 180일 이상 방치 ─ 포인트 글자색으로 강조 (DESIGN 4.2절)
}

/**
 * 카드 두 번째 줄의 '상태 · ○○' 부분 (DESIGN 3.2절 표)
 * 미시작은 플레이타임(0시간) 대신 방치일수 ─ 이 앱이 풀려는 문제가 목록에서 바로 보이게
 */
export function cardMetric(entry: Pick<Entry, 'status' | 'purchased_at' | 'playtime_minutes'>, today: Date = new Date()): CardMetric {
  if (entry.status === 'BACKLOG') {
    const days = idleDays(entry.purchased_at, today)
    if (days === null) return { text: null, loud: false }
    return { text: `방치 ${days}일`, loud: days >= 180 }
  }
  return { text: formatPlaytime(entry.playtime_minutes), loud: false }
}

// S-04 출처 표시 (DESIGN 3.4절)
export const SOURCE_LABEL: Record<Entry['source'], string> = {
  MANUAL: '직접 입력',
  STEAM: 'Steam 연동',
}

// 값이 없을 때의 자리 ─ 빈칸으로 두면 "아직 불러오는 중인가?"로 읽힌다 (DESIGN 3.4절 시간당 비용 '—')
export const EMPTY_VALUE = '—'

/** 원 단위 숫자 → '66,000'. 천 단위 쉼표는 지역 설정과 상관없이 한국 표기로 고정한다 */
export function formatWon(won: number): string {
  return won.toLocaleString('ko-KR')
}

/** 평점 · 한줄평이 보이는 상태 ─ 다른 상태에서는 값이 있어도 숨기기만 한다 (DESIGN 4.3절) */
export function showsRating(status: EntryStatus): boolean {
  return status === 'CLEARED' || status === 'DROPPED'
}

/** 커버가 없을 때 보여줄 제목 앞 두 글자 (DESIGN 4.4절). 공백은 건너뛴다 */
export function titleInitials(title: string): string {
  return Array.from(title.replace(/\s+/g, '')).slice(0, 2).join('')
}
