import { describe, it, expect, vi, afterEach } from 'vitest'
import { CalendarDate } from '@internationalized/date'
import { fromCalendarDate, toCalendarDate, yearRange } from './date-field'

// 구매일 칸 (DESIGN 3.3절) ─ 하루 어긋나면 방치일수가 틀린다

afterEach(() => vi.unstubAllEnvs())

describe('구매일 값 변환', () => {
  it('글자 그대로 오간다', () => {
    expect(fromCalendarDate(toCalendarDate('2026-01-15'))).toBe('2026-01-15')
    expect(fromCalendarDate(toCalendarDate('2024-02-29'))).toBe('2024-02-29')
  })

  it.each(['Asia/Seoul', 'Pacific/Kiritimati', 'Pacific/Pago_Pago'])('%s에서도 하루 어긋나지 않는다', (tz) => {
    vi.stubEnv('TZ', tz)
    expect(fromCalendarDate(toCalendarDate('2026-11-04'))).toBe('2026-11-04')
  })

  it('비었거나 잘못된 글자는 값 없음', () => {
    expect(toCalendarDate('')).toBeUndefined()
    expect(toCalendarDate('2026-13-40')).toBeUndefined()
    expect(toCalendarDate('어제')).toBeUndefined()
  })

  it('지우면 빈 글자', () => {
    expect(fromCalendarDate(undefined)).toBe('')
  })
})

describe('연도 목록', () => {
  const today = new CalendarDate(2026, 11, 4)

  it('1990년부터 내년까지', () => {
    const years = yearRange(today).map((d) => d.year)
    expect(years[0]).toBe(1990)
    expect(years.at(-1)).toBe(2027)
  })

  it('이미 적은 날짜가 범위 밖이면 그 해까지 넓힌다 ─ 수정 화면에서 값이 사라지지 않게', () => {
    expect(yearRange(today, new CalendarDate(1985, 1, 1))[0]!.year).toBe(1985)
    expect(yearRange(today, new CalendarDate(2030, 1, 1)).at(-1)!.year).toBe(2030)
  })
})
