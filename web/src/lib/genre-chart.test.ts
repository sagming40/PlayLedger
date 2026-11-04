import { describe, it, expect } from 'vitest'
import type { GenreStat } from '@/api/stats'
import { formatPercent, formatPlaytime, localToday } from './entry-display'
import { genreChartOption, genreDetail, type ChartColors } from './genre-chart'

// 장르 차트 설정 · 통계 글자 (DESIGN 3.5절)

const COLORS: ChartColors = {
  bar: '#d12e34',
  track: '#22222a',
  label: '#a1a1ac',
  value: '#f2f2f5',
  tooltipBg: '#17171c',
  tooltipBorder: '#2c2c35',
  fontFamily: 'Inter',
}

function genre(patch: Partial<GenreStat>): GenreStat {
  return { genre_id: 1, name: '액션', total: 8, started: 6, cleared: 3, completion_rate: 50, avg_playtime_minutes: 1197, ...patch }
}

describe('장르 차트 설정', () => {
  it('받은 순서대로 위에서부터 그리고, 축은 0 ~ 100 고정이다', () => {
    const option = genreChartOption([genre({ name: '캐주얼', completion_rate: 66.7 }), genre({ name: '액션' })], COLORS, true)
    expect(option.yAxis[0]!.data).toEqual(['캐주얼', '액션'])
    expect(option.yAxis[0]!.inverse).toBe(true)
    expect(option.yAxis[1]!.data).toEqual(['66.7%', '50.0%'])
    expect(option.series[0]!.data).toEqual([66.7, 50])
    expect(option.xAxis).toMatchObject({ min: 0, max: 100 })
  })

  it('시작한 게임이 없는 장르는 막대 없이 — 로, 0%는 0.0%로 그린다', () => {
    const option = genreChartOption(
      [genre({ completion_rate: 0 }), genre({ started: 0, completion_rate: null, avg_playtime_minutes: null })],
      COLORS,
      true,
    )
    expect(option.series[0]!.data).toEqual([0, null])
    expect(option.yAxis[1]!.data).toEqual(['0.0%', '—'])
  })

  it('동작 줄이기를 켜면 움직이지 않는다', () => {
    expect(genreChartOption([genre({})], COLORS, false).animation).toBe(false)
  })

  it('툴팁에 막대에 없는 숫자를 보여 준다', () => {
    const genres = [genre({})]
    const { formatter } = genreChartOption(genres, COLORS, true).tooltip
    expect(formatter([{ dataIndex: 0 }])).toBe('액션<br/>보유 8 · 시작 6 · 클리어 3 · 평균 20.0시간')
    expect(formatter([])).toBe('')
  })

  it('시작한 게임이 없으면 평균은 —', () => {
    expect(genreDetail(genre({ started: 0, cleared: 0, avg_playtime_minutes: null }))).toBe('보유 8 · 시작 0 · 클리어 0 · 평균 —')
  })
})

describe('통계 글자', () => {
  it('비율은 소수 한 자리, 없으면 —', () => {
    expect(formatPercent(42.3)).toBe('42.3%')
    expect(formatPercent(50)).toBe('50.0%')
    expect(formatPercent(0)).toBe('0.0%')
    expect(formatPercent(null)).toBe('—')
  })

  it('시간은 소수 오차 없이 반올림한다', () => {
    expect(formatPlaytime(1197)).toBe('20.0시간') // 19.95
    expect(formatPlaytime(750)).toBe('12.5시간')
    expect(formatPlaytime(100)).toBe('1.7시간')
    expect(formatPlaytime(0)).toBe('0.0시간')
  })

  it('오늘은 그 지역 날짜다 ─ 자정 직후에도', () => {
    expect(localToday(new Date(2026, 10, 4, 0, 30))).toBe('2026-11-04')
    expect(localToday(new Date(2026, 0, 5, 23, 59))).toBe('2026-01-05')
  })
})
