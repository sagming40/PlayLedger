import { describe, it, expect, vi } from 'vitest'
import {
  cardMetric,
  formatPlaytime,
  formatWon,
  idleDays,
  parseGenreFilter,
  parseSort,
  parseStatusFilter,
  titleInitials,
} from './entry-display'

// 카드에 보이는 글자 (DESIGN 3.2 · 4.2절)
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
    // 경계 ─ 딱 180일부터 강조 (DESIGN 4.2절 "180일 이상")
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

  // DESIGN 3.2절 표의 네 줄 그대로 ─ 구매일이 180일을 넘어도 미시작이 아니면 방치로 세지 않는다
  it.each([
    ['PLAYING', 750, '12.5시간'],
    ['CLEARED', 3744, '62.4시간'],
    ['ON_HOLD', 480, '8.0시간'],
    ['DROPPED', 72, '1.2시간'],
  ] as const)('%s는 플레이타임 (분 → 시간, 소수 한 자리)', (status, playtime_minutes, text) => {
    expect(cardMetric({ status, purchased_at: '2026-01-15', playtime_minutes }, TODAY)).toEqual({ text, loud: false })
  })

  it('미시작이 아니면 플레이타임이 0이어도 그대로 보인다', () => {
    expect(cardMetric({ status: 'PLAYING', purchased_at: null, playtime_minutes: 0 }, TODAY)).toEqual({ text: '0.0시간', loud: false })
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

describe('S-04 상세 표시', () => {
  it('원 단위는 천 단위 쉼표', () => {
    expect(formatWon(66000)).toBe('66,000')
    expect(formatWon(1058)).toBe('1,058')
    expect(formatWon(0)).toBe('0')
  })
})

describe('주소의 상태 필터 (DESIGN 2.1절)', () => {
  it('없거나 비었으면 전체(null)', () => {
    expect(parseStatusFilter(undefined)).toBeNull()
    expect(parseStatusFilter('')).toBeNull()
    expect(parseStatusFilter(null)).toBeNull()
  })

  it('아는 상태만 받고, 모르는 값은 undefined ─ 화면이 주소를 고쳐 쓴다', () => {
    expect(parseStatusFilter('BACKLOG')).toBe('BACKLOG')
    expect(parseStatusFilter('backlog')).toBeUndefined()
    expect(parseStatusFilter('toString')).toBeUndefined() // 객체 기본 속성 이름도 상태가 아니다
  })

  it('여러 개가 오면 첫 값만 본다', () => {
    expect(parseStatusFilter(['PLAYING', 'CLEARED'])).toBe('PLAYING')
  })
})

describe('주소의 정렬 · 장르 값', () => {
  it('정렬: 없으면 기본값, 모르는 값은 undefined', () => {
    expect(parseSort(undefined)).toBe('updated')
    expect(parseSort('')).toBe('updated')
    expect(parseSort('title')).toBe('title')
    expect(parseSort(['playtime', 'title'])).toBe('playtime')
    expect(parseSort('price')).toBeUndefined()
    expect(parseSort('toString')).toBeUndefined()
  })

  it('장르: 없으면 null, SERVER가 422로 답할 값은 undefined', () => {
    expect(parseGenreFilter(undefined)).toBeNull()
    expect(parseGenreFilter('3')).toBe(3)
    expect(parseGenreFilter(['3', '4'])).toBe(3)
    expect(parseGenreFilter('2147483647')).toBe(2147483647)
    for (const bad of ['0', '-1', '2147483648', '1.5', 'abc', '03']) expect(parseGenreFilter(bad)).toBeUndefined()
  })
})
