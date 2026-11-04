import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { PAGE_SIZE, useEntryList } from './useEntryList'
import { setAccessToken } from '@/api/client'
import type { Entry, EntryStatus } from '@/api/entries'

// S-02 목록 불러오기 (DESIGN 3.2 · 6장)
// 20개씩 추가 로드 · 겹친 요청 · 중복 기록 · 실패를 가짜 SERVER로 만든다

function json(status: number, body?: unknown) {
  return { ok: status >= 200 && status < 300, status, json: vi.fn().mockResolvedValue(body) } as unknown as Response
}

function entry(id: number): Entry {
  return {
    id,
    game: { id, title: `게임 ${id}`, steam_appid: null, cover_url: null, genres: [] },
    status: 'BACKLOG',
    purchased_at: null,
    purchase_price: null,
    playtime_minutes: 0,
    rating: null,
    review: null,
    source: 'MANUAL',
    cost_per_hour: null,
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

// 상태 칩만 바꾸는 경우 ─ 나머지 필터는 그대로 (LibraryView가 setFilters로 하는 일)
function setStatus(list: ReturnType<typeof useEntryList>, status: EntryStatus | null) {
  return list.setFilters({ status, genre: list.genre.value, sort: list.sort.value })
}

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

// 상태가 섞인 가짜 SERVER ─ status · limit · offset을 실제처럼 거른다
function statusServer(statuses: EntryStatus[]) {
  const all = statuses.map((status, i) => ({ ...entry(i + 1), status }))
  const calls: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(url)
      const q = new URL(url, 'http://x').searchParams
      const rows = q.get('status') ? all.filter((e) => e.status === q.get('status')) : all
      const offset = Number(q.get('offset'))
      return json(200, { items: rows.slice(offset, offset + Number(q.get('limit'))), total: rows.length })
    }),
  )
  return calls
}

describe('상태 필터 (DESIGN 3.2 · 5장)', () => {
  it('고른 상태만 받고, 요약 줄은 라이브러리 전체 기준', async () => {
    statusServer(['BACKLOG', 'PLAYING', 'CLEARED', 'CLEARED', 'BACKLOG'])
    const list = useEntryList()

    await setStatus(list, 'CLEARED')

    expect(list.items.value.map((e) => e.status)).toEqual(['CLEARED', 'CLEARED'])
    expect(list.total.value).toBe(2)
    expect(list.libraryTotal.value).toBe(5)
    expect(list.backlogTotal.value).toBe(2)
  })

  it('목록 응답으로 알 수 있는 개수는 다시 묻지 않는다', async () => {
    const calls = statusServer(['BACKLOG', 'PLAYING'])
    const list = useEntryList()

    await setStatus(list, null)
    // 전체 목록 + 미시작 개수 = 2번 (전체 개수는 목록 total)
    expect(calls).toHaveLength(2)

    calls.length = 0
    await setStatus(list, 'BACKLOG')
    // 미시작 목록 + 전체 개수 = 2번 (미시작 개수는 목록 total)
    expect(calls).toHaveLength(2)
    expect(calls.every((c) => c.includes('limit=1') || c.includes('status=BACKLOG'))).toBe(true)
  })

  it('이 상태만 없으면 "필터 결과 없음", 라이브러리가 비었으면 "빈 상태"', async () => {
    statusServer(['BACKLOG'])
    const list = useEntryList()
    await setStatus(list, 'DROPPED')
    expect(list.isFilterEmpty.value).toBe(true)
    expect(list.isEmpty.value).toBe(false)

    statusServer([])
    const fresh = useEntryList()
    // 새 계정이 ?status=CLEARED 주소로 들어와도 등록을 권한다
    await setStatus(fresh, 'CLEARED')
    expect(fresh.isEmpty.value).toBe(true)
    expect(fresh.isFilterEmpty.value).toBe(false)
  })

  it('필터를 빠르게 바꾸면 늦게 온 앞 필터의 답은 버린다', async () => {
    const held: { url: string; reply: (r: Response) => void }[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => new Promise<Response>((reply) => held.push({ url, reply }))),
    )
    const list = useEntryList()

    const first = setStatus(list, 'PLAYING')
    const second = setStatus(list, 'CLEARED')
    // 뒤 필터(CLEARED)의 답이 먼저, 앞 필터(PLAYING)의 답이 나중에 온다
    for (const h of held.filter((h) => !h.url.includes('PLAYING'))) {
      const cleared = h.url.includes('status=CLEARED')
      h.reply(json(200, { items: cleared ? [{ ...entry(2), status: 'CLEARED' }] : [], total: cleared ? 1 : 3 }))
    }
    await second
    for (const h of held.filter((h) => h.url.includes('PLAYING')))
      h.reply(json(200, { items: [{ ...entry(1), status: 'PLAYING' }], total: 1 }))
    await first

    expect(list.status.value).toBe('CLEARED')
    expect(list.items.value.map((e) => e.id)).toEqual([2])
    expect(list.firstLoading.value).toBe(false)
  })

  it('추가로 불러오는 중에 필터를 바꾸면 그 페이지를 새 목록에 붙이지 않는다', async () => {
    statusServer(Array.from({ length: 25 }, () => 'BACKLOG' as EntryStatus))
    const list = useEntryList()
    await setStatus(list, null)

    // 추가 페이지 요청만 붙잡아 둔다
    const realFetch = globalThis.fetch
    let releaseMore: (() => void) | null = null
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string, init?: RequestInit) =>
        url.includes('offset=20')
          ? new Promise<Response>((resolve) => (releaseMore = () => resolve(realFetch(url, init) as unknown as Response)))
          : realFetch(url, init),
      ),
    )
    const more = list.loadMore()
    await setStatus(list, 'PLAYING')
    releaseMore!()
    await more

    expect(list.items.value).toEqual([])
    expect(list.total.value).toBe(0)
    expect(list.loadingMore.value).toBe(false)
  })

  it('같은 필터를 다시 고르면 다시 부르지 않는다', async () => {
    const calls = statusServer(['BACKLOG'])
    const list = useEntryList()
    await setStatus(list, 'BACKLOG')
    calls.length = 0

    await setStatus(list, 'BACKLOG')

    expect(calls).toHaveLength(0)
  })
})

describe('장르 필터 · 정렬 (REQUIREMENTS F-03, DESIGN 3.2절)', () => {
  const pageCalls = (calls: string[]) => calls.filter((c) => c.includes('limit=20'))

  it('고른 값을 첫 페이지와 추가 페이지 요청에 같이 보낸다', async () => {
    const { calls } = fakeServer(45)
    const list = useEntryList()
    await list.setFilters({ status: 'PLAYING', genre: 3, sort: 'title' })
    await list.loadMore()
    const pages = pageCalls(calls)
    expect(pages).toHaveLength(2)
    for (const url of pages) {
      expect(url).toContain('status=PLAYING')
      expect(url).toContain('genre=3')
      expect(url).toContain('sort=title')
    }
    expect(pages[1]).toContain('offset=20')
  })

  it('기본 정렬은 주소에 적지 않는다', async () => {
    const { calls } = fakeServer(1)
    const list = useEntryList()
    await list.setFilters({ status: null, genre: null, sort: 'updated' })
    expect(pageCalls(calls)[0]).not.toContain('sort=')
  })

  it('장르를 걸면 요약 줄 개수를 목록 total로 대신하지 않는다', async () => {
    const { calls } = fakeServer(5, 2)
    const list = useEntryList()
    await list.setFilters({ status: null, genre: 3, sort: 'updated' })
    const counts = calls.filter((c) => c.includes('limit=1&') || c.endsWith('limit=1'))
    expect(counts.some((c) => !c.includes('status=') && !c.includes('genre='))).toBe(true)
    expect(counts.some((c) => c.includes('status=BACKLOG') && !c.includes('genre='))).toBe(true)
    expect(list.libraryTotal.value).toBe(5)
    expect(list.backlogTotal.value).toBe(2)
  })

  it('정렬을 바꾸면 앞 목록을 비우고 첫 페이지부터 다시 받는다', async () => {
    fakeServer(45)
    const list = useEntryList()
    await list.setFilters({ status: null, genre: null, sort: 'updated' })
    await list.loadMore()
    expect(list.items.value).toHaveLength(40)
    const loading = list.setFilters({ status: null, genre: null, sort: 'playtime' })
    expect(list.items.value).toHaveLength(0)
    await loading
    expect(list.items.value).toHaveLength(20)
  })

  it('장르만 걸어 비면 "필터 결과 없음", 라이브러리가 비면 "빈 상태"', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => json(200, { items: [], total: url.includes('genre=') ? 0 : 5 })),
    )
    const list = useEntryList()
    await list.setFilters({ status: null, genre: 3, sort: 'updated' })
    expect(list.isFilterEmpty.value).toBe(true)
    expect(list.isEmpty.value).toBe(false)

    fakeServer(0)
    const empty = useEntryList()
    await empty.setFilters({ status: null, genre: 3, sort: 'updated' })
    expect(empty.isEmpty.value).toBe(true)
    expect(empty.isFilterEmpty.value).toBe(false)
  })

  it('같은 값을 다시 고르면 다시 부르지 않는다', async () => {
    const { calls } = fakeServer(3)
    const list = useEntryList()
    await list.setFilters({ status: null, genre: 3, sort: 'title' })
    calls.length = 0
    await list.setFilters({ status: null, genre: 3, sort: 'title' })
    expect(calls).toHaveLength(0)
  })
})
