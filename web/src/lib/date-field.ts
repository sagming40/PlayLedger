// 구매일 칸의 값 변환 (DESIGN 3.3절)
// 저장 값은 글자 'YYYY-MM-DD'다 ─ 시각이 없는 CalendarDate로만 바꾼다. Date로 읽으면 한국 시간으로 하루 전날이 될 수 있다 (CLAUDE.md 함정)

import { CalendarDate, parseDate, type DateValue } from '@internationalized/date'

// 달력의 연도 목록 시작 ─ 그보다 오래된 구매일을 이미 적었으면 그 해까지 넓힌다
const FIRST_YEAR = 1990

/** 'YYYY-MM-DD' → 달력 값. 비었거나 잘못된 글자면 undefined ─ 달력은 오늘 달을 보여 준다 */
export function toCalendarDate(ymd: string): CalendarDate | undefined {
  try {
    return ymd ? parseDate(ymd) : undefined
  } catch {
    return undefined
  }
}

/** 달력 값 → 'YYYY-MM-DD'. 지우면 빈 글자 */
export function fromCalendarDate(value: DateValue | undefined): string {
  return value ? value.toString().slice(0, 10) : ''
}

/** 연도 목록 ─ 올해 + 1년까지. 미래 날짜를 막지는 않는다 (입력 실수는 방치 0일로 본다) */
export function yearRange(today: DateValue, selected?: DateValue): DateValue[] {
  const first = Math.min(FIRST_YEAR, selected?.year ?? FIRST_YEAR)
  const last = Math.max(today.year + 1, selected?.year ?? 0)
  return Array.from({ length: last - first + 1 }, (_, i) => new CalendarDate(first + i, 1, 1))
}
