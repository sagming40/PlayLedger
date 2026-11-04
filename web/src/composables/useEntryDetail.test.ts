import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { effectScope } from 'vue'
import { useEntryDetail } from './useEntryDetail'
import { setAccessToken } from '@/api/client'
import type { Entry } from '@/api/entries'
import { toast } from '@/lib/toast'

// S-04 상세 불러오기 · 상태 변경 (DESIGN 3.4 · 4.3 · 6장)
// 늦게 온 답 · 실패 · 다른 탭에서 지운 기록을 가짜 SERVER로 만든다

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

// 기록을 불러온 상세 하나 ─ 삭제 시나리오의 출발점
async function openedDetail() {
  const held = heldServer()
  const detail = useEntryDetail()
  const loading = detail.load(1)
  await flush()
  held.shift()!.reply(json(200, entry(1)))
  await loading
  return { held, detail }
}

describe('삭제', () => {
  it('DELETE를 보내고 성공을 알린다 ─ 204는 본문이 없다', async () => {
    const { held, detail } = await openedDetail()
    const removing = detail.remove()
    await flush()
    expect(held[0]!.init?.method).toBe('DELETE')
    expect(held[0]!.url).toContain('/entries/1')
    held[0]!.reply(json(204))
    expect(await removing).toBe(true)
    expect(detail.saving.value).toBe(false)
    expect(toast.value?.text).toBe('삭제했어요')
  })

  it('두 번 눌러도 한 번만 보낸다', async () => {
    const { held, detail } = await openedDetail()
    const removing = detail.remove()
    expect(await detail.remove()).toBe(false)
    await flush()
    expect(held).toHaveLength(1)
    held[0]!.reply(json(204))
    expect(await removing).toBe(true)
  })

  it('상태 저장 중에는 지우지 않고, 지우는 중에는 상태를 저장하지 않는다', async () => {
    const { held, detail } = await openedDetail()
    const saving = detail.changeStatus('PLAYING')
    expect(await detail.remove()).toBe(false)
    await flush()
    expect(held).toHaveLength(1)
    held[0]!.reply(json(200, entry(1, { status: 'PLAYING' })))
    await saving

    const removing = detail.remove()
    expect(await detail.changeStatus('CLEARED')).toBe(false)
    await flush()
    expect(held.filter((h) => h.init?.method === 'DELETE')).toHaveLength(1)
    expect(held).toHaveLength(2)
    held[1]!.reply(json(204))
    await removing
  })

  it('실패하면 기록을 그대로 두고 이유를 보인다', async () => {
    const { held, detail } = await openedDetail()
    const removing = detail.remove()
    await flush()
    held[0]!.reply(json(500, { detail: 'Internal Server Error' }))
    expect(await removing).toBe(false)
    expect(detail.entry.value?.id).toBe(1)
    expect(detail.deleteError.value).not.toBeNull()
    expect(toast.value).toBeNull()
  })

  it('상세 화면에서 바로 고치는 값은 알리지 않는다 ─ 값이 눈앞에서 바뀐다', async () => {
    const { held, detail } = await openedDetail()
    const saving = detail.changeStatus('PLAYING')
    await flush()
    held[0]!.reply(json(200, entry(1, { status: 'PLAYING' })))
    await saving
    expect(toast.value).toBeNull()
  })

  it('네트워크가 끊기면 연결 실패로 알린다', async () => {
    const { detail } = await openedDetail()
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    expect(await detail.remove()).toBe(false)
    expect(detail.deleteError.value).toBe('연결에 실패했습니다')
  })

  it('다른 탭에서 먼저 지웠으면 "찾을 수 없음"으로 바뀐다', async () => {
    const { held, detail } = await openedDetail()
    const removing = detail.remove()
    await flush()
    held[0]!.reply(json(404, { detail: '기록을 찾을 수 없습니다' }))
    expect(await removing).toBe(false)
    expect(detail.notFound.value).toBe(true)
    expect(detail.entry.value).toBeNull()
    // 이번 요청이 지운 것이 아니다
    expect(toast.value).toBeNull()
  })

  it('답을 기다리는 사이 화면을 떠나면 성공해도 끌고 가지 않는다', async () => {
    const scope = effectScope()
    const held = heldServer()
    const detail = scope.run(() => useEntryDetail())!
    const loading = detail.load(1)
    await flush()
    held.shift()!.reply(json(200, entry(1)))
    await loading
    const removing = detail.remove()
    await flush()
    scope.stop()
    held[0]!.reply(json(204))
    expect(await removing).toBe(false)
  })

  it('답을 기다리는 사이 다른 게임으로 옮기면 그 게임을 건드리지 않는다', async () => {
    const { held, detail } = await openedDetail()
    const removing = detail.remove()
    await flush()
    const loading = detail.load(2)
    await flush()
    held[1]!.reply(json(200, entry(2)))
    await loading
    held[0]!.reply(json(404, { detail: '기록을 찾을 수 없습니다' }))
    expect(await removing).toBe(false)
    expect(detail.entry.value?.id).toBe(2)
    expect(detail.notFound.value).toBe(false)
  })
})

beforeEach(() => {
  setAccessToken('t1')
  toast.value = null
})

afterEach(() => {
  vi.unstubAllGlobals()
  setAccessToken(null)
})

describe('불러오기', () => {
  it('기록을 받아 둔다', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => json(200, entry(7))),
    )
    const d = useEntryDetail()

    await d.load(7)

    expect(d.entry.value?.id).toBe(7)
    expect(d.loading.value).toBe(false)
    expect(d.notFound.value).toBe(false)
  })

  it('없거나 남의 기록(404)은 "찾을 수 없음" 하나로 ─ 오류 문구와 구분한다', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => json(404, { detail: '기록을 찾을 수 없습니다' })),
    )
    const d = useEntryDetail()

    await d.load(7)

    expect(d.notFound.value).toBe(true)
    expect(d.loadError.value).toBeNull()
    expect(d.entry.value).toBeNull()
  })

  it('네트워크가 끊기면 연결 실패 문구', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new TypeError('Failed to fetch')
      }),
    )
    const d = useEntryDetail()

    await d.load(7)

    expect(d.loadError.value).toBe('연결에 실패했습니다')
    expect(d.notFound.value).toBe(false)
  })

  it('상세에서 상세로 빠르게 옮기면 늦게 온 앞 게임의 답은 버린다', async () => {
    const held = heldServer()
    const d = useEntryDetail()

    const first = d.load(1)
    const second = d.load(2)
    // 뒤에 부른 2번이 먼저 오고, 1번이 늦게 온다
    held[1]!.reply(json(200, entry(2)))
    await second
    held[0]!.reply(json(200, entry(1)))
    await first

    expect(d.entry.value?.id).toBe(2)
    expect(d.loading.value).toBe(false)
  })

  it('다른 게임으로 옮기면 답이 오기 전까지 앞 게임을 보여 주지 않는다', async () => {
    const held = heldServer()
    const d = useEntryDetail()
    const first = d.load(1)
    held[0]!.reply(json(200, entry(1)))
    await first

    d.load(2)

    expect(d.entry.value).toBeNull()
    expect(d.loading.value).toBe(true)
    expect(held).toHaveLength(2)
  })
})

describe('상태 변경', () => {
  async function loaded(e: Entry) {
    const held = heldServer()
    const d = useEntryDetail()
    const p = d.load(e.id)
    held[0]!.reply(json(200, e))
    await p
    return { d, held }
  }

  it('상태만 보낸다 ─ 평점 · 한줄평은 건드리지 않는다 (DESIGN 4.3절)', async () => {
    const { d, held } = await loaded(entry(7))

    const p = d.changeStatus('PLAYING')
    expect(held[1]!.init?.method).toBe('PATCH')
    expect(JSON.parse(String(held[1]!.init?.body))).toEqual({ status: 'PLAYING' })
    held[1]!.reply(json(200, entry(7, { status: 'PLAYING' })))
    await p

    expect(d.entry.value?.status).toBe('PLAYING')
    // 평점은 숨기기만 하고 값은 남아 있다
    expect(d.entry.value?.rating).toBe(4)
  })

  it('고르자마자 화면에 반영하고, 저장 중에는 다시 바꿀 수 없다', async () => {
    const { d, held } = await loaded(entry(7))

    d.changeStatus('PLAYING')
    expect(d.entry.value?.status).toBe('PLAYING')
    expect(d.saving.value).toBe(true)

    // 저장이 끝나기 전에 또 고르면 요청을 보내지 않는다 ─ 두 답이 거꾸로 오면 화면과 DB가 갈린다
    d.changeStatus('ON_HOLD')
    expect(held).toHaveLength(2)
    expect(d.entry.value?.status).toBe('PLAYING')
  })

  it('실패하면 원래 상태로 되돌리고 이유를 보여 준다', async () => {
    const { d, held } = await loaded(entry(7))

    const p = d.changeStatus('PLAYING')
    held[1]!.reply(json(500, { detail: '서버에 문제가 생겼습니다. 잠시 후 다시 시도해 주세요' }))
    await p

    expect(d.entry.value?.status).toBe('CLEARED')
    expect(d.saveError.value).toBe('서버에 문제가 생겼습니다. 잠시 후 다시 시도해 주세요')
    expect(d.saving.value).toBe(false)
    expect(d.failedField.value).toBe('status')
  })

  it('다른 탭에서 지운 기록이면(404) 찾을 수 없음으로 바뀐다', async () => {
    const { d, held } = await loaded(entry(7))

    const p = d.changeStatus('PLAYING')
    held[1]!.reply(json(404, { detail: '기록을 찾을 수 없습니다' }))
    await p

    expect(d.notFound.value).toBe(true)
    expect(d.entry.value).toBeNull()
  })

  it('같은 상태를 고르면 요청하지 않는다', async () => {
    const { d, held } = await loaded(entry(7))

    await d.changeStatus('CLEARED')

    expect(held).toHaveLength(1)
  })

  it('저장하는 사이 다른 게임으로 옮기면 앞 게임의 답으로 덮어쓰지 않는다', async () => {
    const { d, held } = await loaded(entry(7))

    const saving = d.changeStatus('PLAYING')
    const moving = d.load(8)
    held[2]!.reply(json(200, entry(8, { status: 'BACKLOG' })))
    await moving
    held[1]!.reply(json(200, entry(7, { status: 'PLAYING' })))
    await saving
    await flush()

    expect(d.entry.value?.id).toBe(8)
    expect(d.entry.value?.status).toBe('BACKLOG')
  })

  it('평점 · 한줄평은 보낸 값으로 PATCH하고 상태는 보내지 않는다', async () => {
    const { d, held } = await loaded(entry(7, { rating: null, review: null }))

    const p = d.rate(3)
    expect(JSON.parse(String(held[1]!.init?.body))).toEqual({ rating: 3 })
    held[1]!.reply(json(200, entry(7, { rating: 3, review: null })))
    await p

    const q = d.saveReview('  다시 할 것 같음  ')
    // 앞뒤 공백은 지워서 보낸다
    expect(JSON.parse(String(held[2]!.init?.body))).toEqual({ review: '다시 할 것 같음' })
    held[2]!.reply(json(200, entry(7, { rating: 3, review: '다시 할 것 같음' })))
    expect(await q).toBe(true)
    expect(d.entry.value?.review).toBe('다시 할 것 같음')
  })
})

describe('평점 · 한줄평', () => {
  async function loaded(e: Entry) {
    const held = heldServer()
    const d = useEntryDetail()
    const p = d.load(e.id)
    held[0]!.reply(json(200, e))
    await p
    return { d, held }
  }

  it('같은 별을 다시 누르면 평점을 지운다 (S-03과 같은 동작)', async () => {
    const { d, held } = await loaded(entry(7, { rating: 4 }))

    const p = d.rate(4)
    expect(JSON.parse(String(held[1]!.init?.body))).toEqual({ rating: null })
    expect(d.entry.value?.rating).toBeNull()
    held[1]!.reply(json(200, entry(7, { rating: null })))
    await p
  })

  it('비운 한줄평은 빈 문자열이 아니라 null로 지운다', async () => {
    const { d, held } = await loaded(entry(7))

    d.saveReview('   ')

    expect(JSON.parse(String(held[1]!.init?.body))).toEqual({ review: null })
  })

  it('한줄평이 그대로면 요청 없이 성공으로 본다 ─ 입력칸은 닫힌다', async () => {
    const { d, held } = await loaded(entry(7, { review: '최고' }))

    expect(await d.saveReview(' 최고 ')).toBe(true)
    expect(held).toHaveLength(1)
  })

  it('평점 저장이 실패하면 되돌리고, 실패한 칸을 알려 준다', async () => {
    const { d, held } = await loaded(entry(7, { rating: 4 }))

    const p = d.rate(2)
    held[1]!.reply(json(500, { detail: 'Internal Server Error' }))
    await p

    expect(d.entry.value?.rating).toBe(4)
    expect(d.failedField.value).toBe('rating')
  })

  it('한줄평 저장이 실패하면 false ─ 화면은 입력칸을 열어 둔다', async () => {
    const { d, held } = await loaded(entry(7, { review: null }))

    const p = d.saveReview('새 한줄평')
    held[1]!.reply(json(422, { detail: [{ loc: ['body', 'review'], type: 'string_too_long' }] }))

    expect(await p).toBe(false)
    expect(d.entry.value?.review).toBeNull()
    expect(d.failedField.value).toBe('review')
  })

  it('저장 중에는 별을 눌러도 요청하지 않는다', async () => {
    const { d, held } = await loaded(entry(7, { rating: 4 }))

    d.changeStatus('DROPPED')
    d.rate(1)

    expect(held).toHaveLength(2)
    expect(d.entry.value?.rating).toBe(4)
  })
})
