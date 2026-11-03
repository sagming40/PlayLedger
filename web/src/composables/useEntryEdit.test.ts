import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { effectScope } from 'vue'
import { useEntryEdit } from './useEntryEdit'
import { setAccessToken } from '@/api/client'
import type { Entry } from '@/api/entries'

// S-03 수정 모드 (DESIGN 3.3 · 4.3절)
// 바뀐 칸만 보내는지 · 실패 · 늦게 온 답 · 다른 탭에서 지운 기록을 가짜 SERVER로 만든다

function json(status: number, body?: unknown) {
  return { ok: status >= 200 && status < 300, status, json: vi.fn().mockResolvedValue(body) } as unknown as Response
}

function entry(id: number, patch: Partial<Entry> = {}): Entry {
  return {
    id,
    game: { id, title: `게임 ${id}`, steam_appid: null, cover_url: null, genres: [] },
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
    ...patch,
  }
}

// 답을 내가 원하는 때에 보내는 가짜 SERVER ─ 요청마다 열쇠(resolve)를 쌓아 둔다
function heldServer() {
  const held: { url: string; init?: RequestInit; reply: (res: Response) => void }[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string, init?: RequestInit) => new Promise<Response>((reply) => held.push({ url, init, reply }))),
  )
  return held
}

async function flush() {
  // fetch → json() → 상태 반영까지 몇 번의 then을 거친다
  for (let i = 0; i < 5; i++) await Promise.resolve()
}

// 기록을 불러온 폼 하나
async function opened(saved: Entry = entry(1)) {
  const held = heldServer()
  const edit = useEntryEdit()
  const loading = edit.load(saved.id)
  await flush()
  held.shift()!.reply(json(200, saved))
  await loading
  return { held, edit }
}

function sentBody(held: { init?: RequestInit }[]) {
  return JSON.parse(held[0]!.init!.body as string)
}

beforeEach(() => {
  setAccessToken('t1')
})

afterEach(() => {
  vi.unstubAllGlobals()
  setAccessToken(null)
})

describe('수정 폼 열기', () => {
  it('기존 값을 채워서 연다', async () => {
    const { edit } = await opened()
    expect(edit.form.value).toEqual({
      status: 'CLEARED',
      genreIds: [],
      purchasedAt: '2026-01-15',
      price: '66000',
      hours: '62.4',
      rating: 4,
      review: '엔딩 보고 한참 멍했음',
    })
    expect(edit.canSubmit.value).toBe(true)
  })

  it('없거나 남의 기록이면 폼을 열지 않는다 ─ 둘 다 같은 404', async () => {
    const held = heldServer()
    const edit = useEntryEdit()
    const loading = edit.load(99)
    await flush()
    held[0]!.reply(json(404, { detail: '찾을 수 없습니다' }))
    await loading
    expect(edit.notFound.value).toBe(true)
    expect(edit.form.value).toBeNull()
    expect(edit.canSubmit.value).toBe(false)
    expect(await edit.submit()).toBe(false)
    expect(held).toHaveLength(1)
  })

  it('다른 게임으로 옮기면 늦게 온 앞 게임의 답을 버린다', async () => {
    const held = heldServer()
    const edit = useEntryEdit()
    const first = edit.load(1)
    await flush()
    const second = edit.load(2)
    await flush()
    held[1]!.reply(json(200, entry(2, { purchase_price: 2000 })))
    await second
    held[0]!.reply(json(200, entry(1, { purchase_price: 1000 })))
    await first
    expect(edit.entry.value?.id).toBe(2)
    expect(edit.form.value?.price).toBe('2000')
  })
})

describe('저장', () => {
  it('바뀐 게 없으면 요청 없이 돌아간다 ─ 목록 순서가 바뀌지 않게', async () => {
    const { held, edit } = await opened()
    expect(await edit.submit()).toBe(true)
    expect(held).toHaveLength(0)
  })

  it('바꾼 칸만 보낸다 ─ 폼을 연 사이 다른 기기에서 고친 칸을 덮어쓰지 않게', async () => {
    const { held, edit } = await opened()
    edit.form.value!.price = '50,000'
    const saving = edit.submit()
    await flush()
    expect(held[0]!.init?.method).toBe('PATCH')
    expect(held[0]!.url).toContain('/entries/1')
    expect(sentBody(held)).toEqual({ purchase_price: 50000 })
    held[0]!.reply(json(200, entry(1)))
    expect(await saving).toBe(true)
  })

  it('클리어 → 플레이중으로 저장해도 평점 · 한줄평을 보내지 않는다 (DESIGN 4.3절)', async () => {
    const { held, edit } = await opened()
    edit.form.value!.status = 'PLAYING'
    const saving = edit.submit()
    await flush()
    expect(sentBody(held)).toEqual({ status: 'PLAYING' })
    held[0]!.reply(json(200, entry(1, { status: 'PLAYING' })))
    await saving
  })

  it('플레이중 → 클리어 + 평점은 한 번에 보낸다', async () => {
    const { held, edit } = await opened(entry(1, { status: 'PLAYING', rating: null, review: null }))
    edit.form.value!.status = 'CLEARED'
    edit.form.value!.rating = 5
    edit.form.value!.review = '  끝까지 해 봄  '
    const saving = edit.submit()
    await flush()
    expect(sentBody(held)).toEqual({ status: 'CLEARED', rating: 5, review: '끝까지 해 봄' })
    held[0]!.reply(json(200, entry(1)))
    await saving
  })

  it('새로 고른 장르가 있을 때만 장르를 보낸다', async () => {
    const { held, edit } = await opened()
    edit.form.value!.genreIds = [1, 3]
    const saving = edit.submit()
    await flush()
    expect(sentBody(held)).toEqual({ genre_ids: [1, 3] })
    held[0]!.reply(json(200, entry(1)))
    await saving
  })

  it('잘못된 입력이면 저장을 막는다', async () => {
    const { held, edit } = await opened()
    edit.form.value!.hours = 'abc'
    expect(edit.canSubmit.value).toBe(false)
    expect(await edit.submit()).toBe(false)
    expect(held).toHaveLength(0)
  })

  it('저장 중에 다시 눌러도 한 번만 보낸다', async () => {
    const { held, edit } = await opened()
    edit.form.value!.price = '1'
    const saving = edit.submit()
    expect(edit.canSubmit.value).toBe(false)
    expect(await edit.submit()).toBe(false)
    await flush()
    expect(held).toHaveLength(1)
    held[0]!.reply(json(200, entry(1)))
    expect(await saving).toBe(true)
  })

  it('실패하면 입력값을 그대로 두고 이유를 보인다', async () => {
    const { held, edit } = await opened()
    edit.form.value!.price = '1'
    const saving = edit.submit()
    await flush()
    held[0]!.reply(json(500, { detail: 'Internal Server Error' }))
    expect(await saving).toBe(false)
    expect(edit.form.value?.price).toBe('1')
    expect(edit.errorMessage.value).not.toBe('')
    expect(edit.canSubmit.value).toBe(true)
  })

  it('Pydantic 422는 영문 대신 칸 이름으로 알린다 (ARCHITECTURE 3.9절)', async () => {
    const { held, edit } = await opened()
    edit.form.value!.review = '길다'
    const saving = edit.submit()
    await flush()
    held[0]!.reply(json(422, { detail: [{ loc: ['body', 'review'], msg: 'too long', type: 'string_too_long' }] }))
    expect(await saving).toBe(false)
    expect(edit.errorMessage.value).toBe('한줄평을(를) 다시 확인해 주세요')
  })

  it('네트워크가 끊기면 연결 실패로 알린다', async () => {
    const { edit } = await opened()
    edit.form.value!.price = '1'
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    expect(await edit.submit()).toBe(false)
    expect(edit.errorMessage.value).toBe('연결에 실패했습니다')
  })

  it('다른 탭에서 지운 기록이면 "찾을 수 없음"으로 바뀐다', async () => {
    const { held, edit } = await opened()
    edit.form.value!.price = '1'
    const saving = edit.submit()
    await flush()
    held[0]!.reply(json(404, { detail: '찾을 수 없습니다' }))
    expect(await saving).toBe(false)
    expect(edit.notFound.value).toBe(true)
    expect(edit.form.value).toBeNull()
  })

  it('저장 답을 기다리는 사이 화면을 떠나면 성공해도 돌아가지 않는다', async () => {
    const scope = effectScope()
    const held = heldServer()
    const edit = scope.run(() => useEntryEdit())!
    const loading = edit.load(1)
    await flush()
    held.shift()!.reply(json(200, entry(1)))
    await loading
    edit.form.value!.price = '1'
    const saving = edit.submit()
    await flush()
    scope.stop()
    held[0]!.reply(json(200, entry(1)))
    expect(await saving).toBe(false)
  })

  it('저장 답을 기다리는 사이 다른 게임으로 옮기면 돌아가지 않는다', async () => {
    const { held, edit } = await opened()
    edit.form.value!.price = '1'
    const saving = edit.submit()
    await flush()
    const loading = edit.load(2)
    await flush()
    held[1]!.reply(json(200, entry(2)))
    await loading
    held[0]!.reply(json(200, entry(1)))
    expect(await saving).toBe(false)
    expect(edit.entry.value?.id).toBe(2)
  })
})
