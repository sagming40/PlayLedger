import { describe, it, expect, vi } from 'vitest'
import { cardMetric, formatPlaytime, idleDays, titleInitials } from './entry-display'

// 카드에 보이는 글자 (UI_DESIGN 3.2 · 4.2절)
// "오늘"을 고정해서 날짜가 바뀌어도 결과가 같게 한다

const TODAY = new Date(2026, 9, 25, 9, 30) // 2026-10-25 09:30 (그 지역 시각)

describe('방치일수', () => {
  it('구매일로부터 오늘까지의 일수', () => {
    expect(idleDays('2026-03-25', TODAY)).toBe(214)
  })

  it('오늘 산 게임은 0일 ─ 날짜를 UTC로 읽으면 시차 때문에 어긋나는 자리', () => {
    expect(idleDays('2026-10-25', TODAY)).toBe(0)
    // 자정 직후에도 같다 (UTC로 읽으면 한국 00:30에 전날로 계산됨)
    expect(idleDays('2026-10-25', new Date(2026, 9, 25, 0, 30))).toBe(0)
    expect(idleDays('2026-10-24', new Date(2026, 9, 25, 0, 30))).toBe(1)
  })

  it('시차가 큰 지역에서도 날짜를 그 지역의 날짜로 읽는다', () => {
    // 한국(+9)에서는 UTC로 잘못 읽어도 반올림에 묻혀 같은 답이 나온다. +14 지역에서는 하루가 틀어진다
    // vi.stubEnv ─ 이 테스트 동안만 시간대를 바꾼다 (Node는 TZ 변경을 바로 반영한다)
    vi.stubEnv('TZ', 'Pacific/Kiritimati')
    try {
      expect(idleDays('2026-10-24', new Date(2026, 9, 25, 9, 30))).toBe(1)
      expect(idleDays('2026-10-25', new Date(2026, 9, 25, 9, 30))).toBe(0)
    } finally {
      vi.unstubAllEnvs()
    }
  })

  it('구매일이 없거나 형식이 다르면 계산하지 않는다', () => {
    expect(idleDays(null, TODAY)).toBeNull()
    expect(idleDays('2026/10/25', TODAY)).toBeNull()
  })

  it('미래 날짜(입력 실수)는 0일로 본다', () => {
    expect(idleDays('2026-12-01', TODAY)).toBe(0)
  })
})

describe('카드 두 번째 줄', () => {
  it('미시작은 플레이타임 대신 방치일수, 180일부터 강조', () => {
    expect(cardMetric({ status: 'BACKLOG', purchased_at: '2026-03-25', playtime_minutes: 0 }, TODAY)).toEqual({
      text: '방치 214일',
      loud: true,
    })
    // 경계 ─ 딱 180일부터 강조 (UI_DESIGN 4.2절 "180일 이상")
    expect(cardMetric({ status: 'BACKLOG', purchased_at: '2026-04-28', playtime_minutes: 0 }, TODAY)).toEqual({
      text: '방치 180일',
      loud: true,
    })
    expect(cardMetric({ status: 'BACKLOG', purchased_at: '2026-04-29', playtime_minutes: 0 }, TODAY)).toEqual({
      text: '방치 179일',
      loud: false,
    })
  })

  it('구매일 없는 미시작은 상태만 보인다', () => {
    expect(cardMetric({ status: 'BACKLOG', purchased_at: null, playtime_minutes: 0 }, TODAY)).toEqual({
      text: null,
      loud: false,
    })
  })

  it('나머지 상태는 플레이타임 (분 → 시간, 소수 한 자리)', () => {
    expect(cardMetric({ status: 'CLEARED', purchased_at: '2026-01-15', playtime_minutes: 3744 }, TODAY)).toEqual({
      text: '62.4시간',
      loud: false,
    })
    expect(formatPlaytime(0)).toBe('0.0시간')
  })
})

describe('커버 대체 표시', () => {
  it('제목 앞 두 글자, 공백은 건너뛴다', () => {
    expect(titleInitials('Hollow Knight')).toBe('Ho')
    expect(titleInitials('  발더스 게이트 3')).toBe('발더')
    expect(titleInitials('Ⅶ')).toBe('Ⅶ')
  })
})
