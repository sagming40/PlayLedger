import { describe, it, expect } from 'vitest'
import { buildCreateBody, buildUpdateBody, canRate, entryToEditForm, issuesMessage, parseHours, parsePrice } from './entry-form'
import type { EntryForm } from './entry-form'
import type { Entry } from '@/api/entries'

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
  it('가입 폼도 어느 칸인지 알려 준다', () => {
    expect(issuesMessage([{ field: 'nickname', rule: 'string_too_short' }])).toContain('닉네임')
    expect(issuesMessage([{ field: 'password', rule: 'string_too_short' }])).toContain('비밀번호')
  })

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

// 수정 폼 (DESIGN 3.3 · 4.3절) ─ 수정 화면이 이 규칙으로 PATCH 본문을 만든다
function saved(over: Partial<Entry> = {}): Entry {
  return {
    id: 7,
    game: { id: 7, title: 'Celeste', steam_appid: null, cover_url: null, genres: [] },
    status: 'CLEARED',
    purchased_at: '2026-01-15',
    purchase_price: 66000,
    playtime_minutes: 3744,
    rating: 4,
    review: '엔딩 보고 한참 멍했음',
    source: 'MANUAL',
    cost_per_hour: 1058,
    created_at: '2026-10-25T00:00:00Z',
    updated_at: '2026-10-25T00:00:00Z',
    ...over,
  }
}

describe('entryToEditForm', () => {
  it('저장된 값을 입력칸 글자로 채운다', () => {
    expect(entryToEditForm(saved())).toEqual({
      genreIds: [],
      status: 'CLEARED',
      purchasedAt: '2026-01-15',
      price: '66000',
      hours: '62.4',
      rating: 4,
      review: '엔딩 보고 한참 멍했음',
    })
  })

  it('없는 값은 빈 칸 ─ 0시간도 빈 칸 (parseHours가 빈 칸을 0으로 읽는다)', () => {
    expect(entryToEditForm(saved({ purchased_at: null, purchase_price: null, playtime_minutes: 0, rating: null, review: null }))).toEqual({
      genreIds: [],
      status: 'CLEARED',
      purchasedAt: '',
      price: '',
      hours: '',
      rating: null,
      review: '',
    })
  })
})

describe('수정 폼의 장르 (decisions/0011)', () => {
  const genres = [
    { id: 1, name: '액션' },
    { id: 3, name: 'RPG' },
  ]
  const manual = saved({ game: { id: 7, title: 'Celeste', steam_appid: null, cover_url: null, genres } })
  const steam = saved({ game: { id: 7, title: 'Celeste', steam_appid: 504230, cover_url: null, genres } })

  it('직접 등록한 게임은 지금 장르를 칩으로 채우고, 그대로면 보내지 않는다', () => {
    const initial = entryToEditForm(manual)
    expect(initial.genreIds).toEqual([1, 3])
    expect(buildUpdateBody({ ...initial, genreIds: [3, 1] }, initial)).toEqual({})
  })

  it('직접 등록한 게임은 바꾸거나 전부 뗄 수 있다', () => {
    const initial = entryToEditForm(manual)
    expect(buildUpdateBody({ ...initial, genreIds: [1] }, initial)).toEqual({ genre_ids: [1] })
    expect(buildUpdateBody({ ...initial, genreIds: [] }, initial)).toEqual({ genre_ids: [] })
  })

  it('Steam 게임은 폼에 담지 않고, 고르지 않으면 보내지 않는다', () => {
    const initial = entryToEditForm(steam)
    expect(initial.genreIds).toEqual([])
    expect(buildUpdateBody({ ...initial }, initial)).toEqual({})
  })
})

describe('buildUpdateBody', () => {
  it('아무것도 안 바꾸면 빈 본문', () => {
    const initial = entryToEditForm(saved())
    expect(buildUpdateBody({ ...initial }, initial)).toEqual({})
  })

  it('CLEARED → PLAYING으로 바꿔도 평점 · 한줄평을 보내지 않는다 ─ 숨기기만 한다 (평점 보존 규칙)', () => {
    const initial = entryToEditForm(saved())
    // 상태를 바꾼 뒤 숨겨진 칸에 무엇이 남아 있든 보내지 않는다
    expect(buildUpdateBody({ ...initial, status: 'PLAYING', rating: null, review: '' }, initial)).toEqual({ status: 'PLAYING' })
  })

  it('숨겨져 있던 평점을 다시 보이는 상태로 돌리면 남아 있던 값이 그대로다 ─ 보낼 것이 상태뿐', () => {
    const initial = entryToEditForm(saved({ status: 'PLAYING' }))
    expect(buildUpdateBody({ ...initial, status: 'CLEARED' }, initial)).toEqual({ status: 'CLEARED' })
  })

  it('보이는 평점을 지우면 null로 지운다 ─ 숨김과 지움은 다르다', () => {
    const initial = entryToEditForm(saved())
    expect(buildUpdateBody({ ...initial, rating: null, review: '  ' }, initial)).toEqual({ rating: null, review: null })
  })

  it('손대지 않은 칸은 보내지 않는다 ─ 다른 기기에서 바꾼 값을 덮어쓰지 않게', () => {
    const initial = entryToEditForm(saved())
    expect(buildUpdateBody({ ...initial, price: '50,000' }, initial)).toEqual({ purchase_price: 50000 })
  })

  it('시간 칸으로 정확히 못 담는 분(100분 → 1.67)도 손대지 않으면 그대로 둔다', () => {
    const initial = entryToEditForm(saved({ playtime_minutes: 100 }))
    expect(initial.hours).toBe('1.67')
    expect(buildUpdateBody({ ...initial, status: 'DROPPED' }, initial)).toEqual({ status: 'DROPPED' })
    // 고치면 고친 값으로
    expect(buildUpdateBody({ ...initial, hours: '2' }, initial)).toEqual({ playtime_minutes: 120 })
  })

  it('구매일 · 구매가를 비우면 null, 숫자 칸이 잘못되면 null(보내지 않음)', () => {
    const initial = entryToEditForm(saved())
    expect(buildUpdateBody({ ...initial, purchasedAt: '', price: '' }, initial)).toEqual({ purchased_at: null, purchase_price: null })
    expect(buildUpdateBody({ ...initial, hours: 'abc' }, initial)).toBeNull()
  })
})
