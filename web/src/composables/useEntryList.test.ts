import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { PAGE_SIZE, useEntryList } from './useEntryList'
import { setAccessToken } from '@/api/client'
import type { Entry } from '@/api/entries'

// S-02 목록 불러오기 (UI_DESIGN 3.2 · 6장)
// 20개씩 추가 로드 · 겹친 요청 · 중복 기록 · 실패를 가짜 SERVER로 만든다

function json(status: number, body?: unknown) {
  return { ok: status >= 200 && status < 300, status, json: vi.fn().mockResolvedValue(body) } as unknown as Response
}

function entry(id: number): Entry {
  return {
    id,
    game: { id, title: `게임 ${id}`, genres: [] },
    status: 'BACKLOG',
    purchased_at: null,
    purchase_price: null,
    playtime_minutes: 0,
    rating: null,
    review: null,
    source: 'MANUAL',
    created_at: '2026-10-25T00:00:00Z',
    updated_at: '2026-10-25T00:00:00Z',
  }
}

// 기록 n개를 가진 가짜 SERVER. limit · offset · status를 실제처럼 처리한다
function fakeServer(count: number, backlogCount = count) {
  const calls: string[] = []
  const all = Array.from({ length: count }, (_, i) => entry(i + 1))
  const fetchMock = vi.fn(async (url: string) => {
    calls.push(url)
    const q = new URL(url, 'http://x').searchParams
    const limit = Number(q.get('limit'))
    const offset = Number(q.get('offset'))
    if (q.get('status') === 'BACKLOG') return json(200, { items: all.slice(0, limit), total: backlogCount })
    return json(200, { items: all.slice(offset, offset + limit), total: count })
  })
  vi.stubGlobal('fetch', fetchMock)
  return { calls, fetchMock, listCalls: () => calls.filter((c) => !c.includes('status=')) }
}

beforeEach(() => {
  setAccessToken('t1')
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('목록 불러오기', () => {
  it('처음에는 20개와 전체 개수 · 미시작 개수를 받는다', async () => {
    fakeServer(25, 7)
    const list = useEntryList()

    await list.loadFirst()

    expect(list.items.value).toHaveLength(PAGE_SIZE)
    expect(list.total.value).toBe(25)
    expect(list.backlogTotal.value).toBe(7)
    expect(list.hasMore.value).toBe(true)
  })

  it('끝에 닿으면 이어서 받고, 다 받으면 더 요청하지 않는다', async () => {
    const server = fakeServer(25)
    const list = useEntryList()
    await list.loadFirst()

    await list.loadMore()
    await list.loadMore()

    expect(list.items.value.map((e) => e.id)).toEqual(Array.from({ length: 25 }, (_, i) => i + 1))
    expect(list.hasMore.value).toBe(false)
    // 첫 페이지 + 둘째 페이지 = 2번. 세 번째 loadMore는 요청하지 않았다
    expect(server.listCalls()).toHaveLength(2)
    expect(server.listCalls()[1]).toContain('offset=20')
  })

  it('스크롤 감지와 버튼이 동시에 불러도 같은 페이지를 한 번만 받는다', async () => {
    const server = fakeServer(45)
    const list = useEntryList()
    await list.loadFirst()

    await Promise.all([list.loadMore(), list.loadMore(), list.loadMore()])

    expect(list.items.value).toHaveLength(40)
    expect(server.listCalls()).toHaveLength(2)
  })

  it('페이지 사이에 순서가 밀려 같은 기록이 다시 오면 하나만 남긴다', async () => {
    const list = useEntryList()
    const first = Array.from({ length: 20 }, (_, i) => entry(i + 1))
    // 둘째 페이지 첫 줄이 이미 받은 20번 (다른 탭에서 수정되어 순서가 밀린 상황)
    const second = [entry(20), entry(21), entry(22)]
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce(json(200, { items: first, total: 22 }))
        .mockResolvedValueOnce(json(200, { items: [], total: 0 }))
        .mockResolvedValueOnce(json(200, { items: second, total: 22 })),
    )
    await list.loadFirst()
    await list.loadMore()

    const ids = list.items.value.map((e) => e.id)
    expect(new Set(ids).size).toBe(ids.length)
    expect(ids.at(-1)).toBe(22)
  })

  it('기록이 0개면 빈 상태 ─ 첫 응답 전에는 빈 상태로 보지 않는다', async () => {
    fakeServer(0)
    const list = useEntryList()
    expect(list.isEmpty.value).toBe(false) // 아직 모름

    await list.loadFirst()

    expect(list.isEmpty.value).toBe(true)
    expect(list.hasMore.value).toBe(false)
  })
})

describe('실패', () => {
  it('처음부터 연결이 끊기면 오류 문구를 남기고, 다시 시도하면 불러온다', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    const list = useEntryList()

    await list.loadFirst()
    expect(list.firstError.value).toBe('연결에 실패했습니다')
    expect(list.firstLoading.value).toBe(false)

    fakeServer(3)
    await list.loadFirst()
    expect(list.firstError.value).toBeNull()
    expect(list.items.value).toHaveLength(3)
  })

  it('추가로 불러오다 실패하면 이미 받은 목록은 그대로 두고 다시 시도할 수 있다', async () => {
    fakeServer(25)
    const list = useEntryList()
    await list.loadFirst()

    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    await list.loadMore()
    expect(list.items.value).toHaveLength(20)
    expect(list.moreError.value).toBe('연결에 실패했습니다')

    fakeServer(25)
    await list.loadMore()
    expect(list.items.value).toHaveLength(25)
    expect(list.moreError.value).toBeNull()
  })

  it('미시작 개수만 실패하면 목록은 보여주고 개수는 비워 둔다', async () => {
    const all = Array.from({ length: 3 }, (_, i) => entry(i + 1))
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) =>
        url.includes('status=BACKLOG') ? json(500, { detail: 'Internal Server Error' }) : json(200, { items: all, total: 3 }),
      ),
    )
    const list = useEntryList()

    await list.loadFirst()

    expect(list.items.value).toHaveLength(3)
    expect(list.backlogTotal.value).toBeNull()
    expect(list.firstError.value).toBeNull()
  })
})
