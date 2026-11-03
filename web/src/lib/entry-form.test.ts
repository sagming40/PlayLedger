import { describe, it, expect } from 'vitest'
import { buildCreateBody, canRate, issuesMessage, parseHours, parsePrice } from './entry-form'
import type { EntryForm } from './entry-form'

// S-03 입력값 변환 (DESIGN 3.3절)

function form(over: Partial<EntryForm> = {}): EntryForm {
  return {
    title: 'Celeste',
    steamApp: null,
    status: 'BACKLOG',
    genreIds: [],
    purchasedAt: '',
    price: '',
    hours: '',
    rating: null,
    review: '',
    ...over,
  }
}

describe('parsePrice', () => {
  it('쉼표를 빼고 읽고, 빈 칸은 null', () => {
    expect(parsePrice('66,000')).toBe(66000)
    expect(parsePrice('  ')).toBeNull()
    expect(parsePrice('0')).toBe(0)
  })

  it('숫자가 아니거나 음수 · 소수 · 범위 밖이면 undefined', () => {
    for (const bad of ['abc', '-1', '1.5', '2147483648']) expect(parsePrice(bad)).toBeUndefined()
  })
})

describe('parseHours', () => {
  it('시간을 분으로 바꾸고, 빈 칸은 0', () => {
    expect(parseHours('1.5')).toBe(90)
    expect(parseHours('')).toBe(0)
    expect(parseHours('62.4')).toBe(3744) // 부동소수 오차가 분에 남지 않는다
  })

  it('숫자가 아니거나 음수 · 범위 밖이면 undefined', () => {
    for (const bad of ['abc', '-1', '1.', '99999999999']) expect(parseHours(bad)).toBeUndefined()
  })
})

describe('canRate', () => {
  it('클리어 · 포기만 평점을 적는다', () => {
    expect(['BACKLOG', 'PLAYING', 'CLEARED', 'ON_HOLD', 'DROPPED'].filter((s) => canRate(s as never))).toEqual(['CLEARED', 'DROPPED'])
  })
})

describe('buildCreateBody', () => {
  it('직접 입력은 제목을 보내고 steam_appid는 없다', () => {
    const body = buildCreateBody(form({ title: '  Celeste ', price: '1,000', hours: '2' }))
    expect(body).toMatchObject({ title: 'Celeste', purchase_price: 1000, playtime_minutes: 120 })
    expect(body).not.toHaveProperty('steam_appid')
  })

  it('Steam 게임은 steam_appid만 보내고 제목은 보내지 않는다 (둘 다 보내면 SERVER가 422)', () => {
    const body = buildCreateBody(form({ title: 'Hollow Knight', steamApp: { appid: 367520, name: 'Hollow Knight' } }))
    expect(body).toMatchObject({ steam_appid: 367520 })
    expect(body).not.toHaveProperty('title')
  })

  it('제목이 비었거나 숫자 칸이 잘못되면 null', () => {
    expect(buildCreateBody(form({ title: '   ' }))).toBeNull()
    expect(buildCreateBody(form({ price: 'abc' }))).toBeNull()
    expect(buildCreateBody(form({ hours: 'abc' }))).toBeNull()
  })

  it('빈 구매일은 null이다 (빈 문자열을 보내면 SERVER가 날짜로 읽지 못해 422)', () => {
    expect(buildCreateBody(form())?.purchased_at).toBeNull()
    expect(buildCreateBody(form({ purchasedAt: '2026-01-15' }))?.purchased_at).toBe('2026-01-15')
  })

  it('상태를 바꿔 숨겨진 평점 · 한줄평은 보내지 않는다', () => {
    const hidden = buildCreateBody(form({ status: 'PLAYING', rating: 5, review: '최고' }))
    expect(hidden).toMatchObject({ rating: null, review: null })

    const shown = buildCreateBody(form({ status: 'CLEARED', rating: 5, review: ' 최고 ' }))
    expect(shown).toMatchObject({ rating: 5, review: '최고' })
  })
})

describe('issuesMessage', () => {
  it('입력칸 이름을 한국어로 모으고, 모르는 칸이면 null', () => {
    expect(
      issuesMessage([
        { field: 'review', rule: 'string_too_long' },
        { field: 'purchase_price', rule: 'less_than_equal' },
        { field: 'review', rule: 'x' },
      ]),
    ).toBe('한줄평 · 구매가을(를) 다시 확인해 주세요')
    expect(issuesMessage([{ field: 'body', rule: 'value_error' }])).toBeNull()
  })
})
