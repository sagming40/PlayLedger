import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { effectScope } from 'vue'
import { SEARCH_DELAY_MS, useSteamSearch } from './useSteamSearch'
import { setAccessToken } from '@/api/client'

// S-03 제목 자동완성 (DESIGN 3.3절)
// 입력 멈춤 · 늦게 온 답 · 실패는 손으로 재현하기 어려워 가짜 SERVER로 만든다

function json(status: number, body?: unknown) {
  return { ok: status >= 200 && status < 300, status, json: vi.fn().mockResolvedValue(body) } as unknown as Response
}

beforeEach(() => {
  vi.useFakeTimers()
  setAccessToken('t')
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
  setAccessToken(null)
})

async function pass(ms = SEARCH_DELAY_MS) {
  await vi.advanceTimersByTimeAsync(ms)
}

describe('useSteamSearch', () => {
  it('입력이 멈춘 뒤 마지막 검색어로 한 번만 부른다', async () => {
    const fetchMock = vi.fn(async () => json(200, [{ appid: 1, name: 'Hollow Knight' }]))
    vi.stubGlobal('fetch', fetchMock)
    const s = useSteamSearch()

    s.search('ho')
    await pass(100)
    s.search('hol')
    await pass(100)
    s.search('holl')
    await pass()

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect((fetchMock.mock.calls[0] as unknown as [string])[0]).toContain('q=holl')
    expect(s.results.value).toEqual([{ appid: 1, name: 'Hollow Knight' }])
    expect(s.searched.value).toBe(true)
  })

  it('두 글자 미만이면 부르지 않고 후보를 비운다', async () => {
    const fetchMock = vi.fn(async () => json(200, [{ appid: 1, name: 'A' }]))
    vi.stubGlobal('fetch', fetchMock)
    const s = useSteamSearch()

    s.search('ho')
    await pass()
    expect(s.results.value).toHaveLength(1)

    s.search(' h ')
    await pass()
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(s.results.value).toEqual([])
    expect(s.searched.value).toBe(false)
  })

  it('늦게 도착한 앞선 답은 버린다', async () => {
    let answerFirst: (r: Response) => void = () => {}
    const first = new Promise<Response>((resolve) => (answerFirst = resolve))
    const fetchMock = vi
      .fn()
      .mockReturnValueOnce(first)
      .mockResolvedValueOnce(json(200, [{ appid: 2, name: 'Hollow Knight' }]))
    vi.stubGlobal('fetch', fetchMock)
    const s = useSteamSearch()

    s.search('ho')
    await pass() // 첫 요청이 나가고 답을 기다린다
    s.search('hollow')
    await pass() // 둘째 요청의 답이 먼저 온다
    answerFirst(json(200, [{ appid: 1, name: '늦은 답' }]))
    await pass(0)

    expect(s.results.value).toEqual([{ appid: 2, name: 'Hollow Knight' }])
    expect(s.searching.value).toBe(false)
  })

  it('실패하면 failed만 켠다 ─ 예외를 내보내지 않는다', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => json(500, { detail: 'Internal Server Error' })))
    const s = useSteamSearch()

    s.search('hollow')
    await pass()

    expect(s.failed.value).toBe(true)
    expect(s.results.value).toEqual([])
    expect(s.searching.value).toBe(false)
  })

  it('검색어에 & 가 있어도 잘리지 않고, 100자로 잘라 보낸다', async () => {
    const fetchMock = vi.fn(async () => json(200, []))
    vi.stubGlobal('fetch', fetchMock)
    const s = useSteamSearch()

    s.search('R&D')
    await pass()
    expect((fetchMock.mock.calls[0] as unknown as [string])[0]).toContain('q=R%26D')

    s.search('가'.repeat(150))
    await pass()
    const q = new URL((fetchMock.mock.calls[1] as unknown as [string])[0], 'http://x').searchParams.get('q')
    expect(q).toHaveLength(100)
  })

  it('화면을 떠나면 예약된 검색이 나가지 않는다', async () => {
    const fetchMock = vi.fn(async () => json(200, []))
    vi.stubGlobal('fetch', fetchMock)
    const scope = effectScope()
    const s = scope.run(() => useSteamSearch())!

    s.search('hollow')
    scope.stop()
    await pass()

    expect(fetchMock).not.toHaveBeenCalled()
  })
})
