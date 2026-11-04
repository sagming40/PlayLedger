import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useStats } from './useStats'
import { setAccessToken } from '@/api/client'
import type { Stats } from '@/api/stats'

// S-05 불러오기 (DESIGN 3.5 · 6장) ─ 늦게 온 답 · 실패를 가짜 SERVER로 만든다

function json(status: number, body?: unknown) {
  return { ok: status >= 200 && status < 300, status, json: vi.fn().mockResolvedValue(body) } as unknown as Response
}

function stats(total: number): Stats {
  return { total, backlog: 0, abandoned_rate: null, completion_rate: null, longest_idle: [], highest_cost: [], genres: [] }
}

function heldServer() {
  const held: { url: string; reply: (res: Response) => void }[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string) => new Promise<Response>((reply) => held.push({ url, reply }))),
  )
  return held
}

async function flush() {
  for (let i = 0; i < 5; i++) await Promise.resolve()
}

beforeEach(() => {
  setAccessToken('t1')
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.useRealTimers()
  setAccessToken(null)
})

describe('통계 불러오기', () => {
  it('브라우저의 오늘을 보낸다 ─ 한국 오전 9시 전이어도 그 지역 날짜', async () => {
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(new Date(2026, 10, 4, 0, 30))
    const held = heldServer()
    const s = useStats()
    const loading = s.load()
    await flush()
    expect(held[0]!.url).toContain('/stats?today=2026-11-04')
    held[0]!.reply(json(200, stats(3)))
    await loading
    expect(s.stats.value?.total).toBe(3)
    expect(s.loading.value).toBe(false)
  })

  it('실패하면 이유를 보이고, 다시 시도하면 지운다', async () => {
    const held = heldServer()
    const s = useStats()
    const first = s.load()
    await flush()
    held[0]!.reply(json(500, { detail: 'Internal Server Error' }))
    await first
    expect(s.error.value).not.toBeNull()
    expect(s.stats.value).toBeNull()

    const second = s.load()
    expect(s.error.value).toBeNull()
    await flush()
    held[1]!.reply(json(200, stats(1)))
    await second
    expect(s.stats.value?.total).toBe(1)
  })

  it('네트워크가 끊기면 연결 실패로 알린다', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    const s = useStats()
    await s.load()
    expect(s.error.value).toBe('연결에 실패했습니다')
  })

  it('늦게 온 앞 요청의 답은 버린다', async () => {
    const held = heldServer()
    const s = useStats()
    const first = s.load()
    await flush()
    const second = s.load()
    await flush()
    held[1]!.reply(json(200, stats(2)))
    await second
    held[0]!.reply(json(200, stats(1)))
    await first
    expect(s.stats.value?.total).toBe(2)
    expect(s.loading.value).toBe(false)
  })
})
