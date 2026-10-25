import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import type { RouteLocationNormalized } from 'vue-router'
import { authGuard, loginRouteAfterSessionEnd, safeRedirect } from './guard'
import { useAuthStore } from '@/stores/auth'
import { request, setAccessToken } from '@/api/client'

// 앱 시작 시 로그인 복원 + 라우터 가드 (UI_DESIGN 2.3절, API_SPEC 3.3절)
// 새로고침 · 쿠키 만료 · 동시 이동처럼 브라우저에서 매번 손으로 만들기 번거로운 상황을 여기서 고정한다

function json(status: number, body?: unknown) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: vi.fn().mockResolvedValue(body),
  } as unknown as Response
}

const ME = { id: 1, email: 'a@example.com', nickname: 'tester', created_at: '2026-10-25T00:00:00Z' }

interface ServerOpts {
  refresh?: () => Response | Promise<Response>
  me?: () => Response | Promise<Response>
}

// 가짜 SERVER ─ refresh · me · logout만 흉내 낸다
function fakeServer(opts: ServerOpts = {}) {
  const calls: { url: string; auth?: string }[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init: RequestInit) => {
      const auth = (init.headers as Record<string, string>)['Authorization']
      calls.push({ url, auth })
      if (url === '/api/auth/refresh') return (opts.refresh ?? (() => json(200, { access_token: 't1' })))()
      if (url === '/api/auth/me') return (opts.me ?? (() => json(200, ME)))()
      if (url === '/api/auth/logout') return json(204)
      return auth ? json(200, {}) : json(401, { detail: '인증이 필요합니다' })
    }),
  )
  return {
    calls,
    count: (path: string) => calls.filter((c) => c.url === `/api${path}`).length,
  }
}

// 가드는 이동할 주소의 일부(name · meta · fullPath · query)만 본다
function to(fullPath: string, extra: Partial<RouteLocationNormalized> = {}): RouteLocationNormalized {
  const [path = '', search = ''] = fullPath.split('?')
  const query = Object.fromEntries(new URLSearchParams(search))
  const name = path === '/login' ? 'login' : path.slice(1)
  const meta = path === '/login' ? { public: true } : {}
  return { fullPath, path, name, meta, query, ...extra } as unknown as RouteLocationNormalized
}

beforeEach(() => {
  // 스토어 · TOKEN이 테스트 사이에 남지 않게 매번 새로 시작한다 ─ 새로고침 직후와 같은 상태
  setActivePinia(createPinia())
  setAccessToken(null)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('safeRedirect', () => {
  it('사이트 안의 주소는 그대로 돌려준다', () => {
    expect(safeRedirect('/library?status=BACKLOG')).toBe('/library?status=BACKLOG')
  })

  it.each([
    ['다른 사이트 주소', 'https://evil.example'],
    ['슬래시 두 개로 시작하는 주소', '//evil.example'],
    ['역슬래시 꼼수', '/\\evil.example'],
    ['로그인 화면 자신', '/login?redirect=/library'],
    ['값 없음', undefined],
  ])('%s는 홈으로 보낸다', (_, value) => {
    expect(safeRedirect(value)).toBe('/library')
  })
})

describe('로그인 복원 + 가드', () => {
  it('새로고침 · COOKIE 살아 있음 ─ refresh 1번, 원래 화면 그대로 (M2 완료 기준 1번)', async () => {
    const server = fakeServer()

    const result = await authGuard(to('/library'))

    expect(result).toBe(true)
    expect(server.count('/auth/refresh')).toBe(1)
    expect(useAuthStore().user).toEqual(ME)
    expect(useAuthStore().isReady).toBe(true)
  })

  it('새로고침 · COOKIE 없음 ─ 오류 없이 로그인 화면으로, 가려던 주소를 기억한다', async () => {
    const server = fakeServer({ refresh: () => json(401, { detail: '인증 정보가 없습니다' }) })

    const result = await authGuard(to('/library?status=BACKLOG'))

    expect(result).toEqual({ name: 'login', query: { redirect: '/library?status=BACKLOG' } })
    expect(server.count('/auth/me')).toBe(0)
    expect(useAuthStore().isReady).toBe(true)
  })

  it('복원 중 이동이 겹쳐도 refresh는 1번만 나간다', async () => {
    let release!: () => void
    const gate = new Promise<void>((r) => (release = r))
    const server = fakeServer({
      refresh: async () => {
        await gate
        return json(200, { access_token: 't1' })
      },
    })

    const first = authGuard(to('/library'))
    const second = authGuard(to('/stats'))
    release()

    await expect(Promise.all([first, second])).resolves.toEqual([true, true])
    expect(server.count('/auth/refresh')).toBe(1)
  })

  it('복원이 끝난 뒤의 이동은 refresh를 다시 보내지 않는다', async () => {
    const server = fakeServer()

    await authGuard(to('/library'))
    await authGuard(to('/stats'))

    expect(server.count('/auth/refresh')).toBe(1)
  })

  it('restore()를 가드 밖에서 다시 불러도 refresh를 또 보내지 않는다', async () => {
    // 가드는 isReady를 먼저 보지만, 다른 곳(예: 화면)에서 restore()를 직접 부를 수도 있다
    // refresh는 rotation이라 불필요한 재발급도 줄여야 한다
    const server = fakeServer()
    const auth = useAuthStore()

    await auth.restore()
    await auth.restore()

    expect(server.count('/auth/refresh')).toBe(1)
  })

  it('로그인한 채로 로그인 화면에 오면 기억한 주소(없으면 홈)로 보낸다', async () => {
    fakeServer()

    await expect(authGuard(to('/login?redirect=/stats'))).resolves.toBe('/stats')
    await expect(authGuard(to('/login'))).resolves.toBe('/library')
  })

  it('로그아웃 후 뒤로가기로 보호된 화면에 오면 로그인 화면으로 밀려난다 (M2 완료 기준 5번)', async () => {
    fakeServer()
    await authGuard(to('/library'))

    await useAuthStore().logout()

    await expect(authGuard(to('/library'))).resolves.toEqual({
      name: 'login',
      query: { redirect: '/library' },
    })
  })

  it('로그인하지 않아도 로그인 화면에는 들어갈 수 있다', async () => {
    fakeServer({ refresh: () => json(401, { detail: '인증 정보가 없습니다' }) })

    await expect(authGuard(to('/login'))).resolves.toBe(true)
  })
})

describe('복원 실패', () => {
  it('refresh는 됐는데 /me가 실패하면 TOKEN도 비운다 ─ 반쯤 로그인된 상태를 남기지 않는다', async () => {
    const server = fakeServer({ me: () => json(500, { detail: 'Internal Server Error' }) })

    const result = await authGuard(to('/library'))

    expect(result).toEqual({ name: 'login', query: { redirect: '/library' } })
    // 이후 요청에 복원 때 받은 TOKEN이 실려 나가지 않는다
    await request('/entries').catch(() => undefined)
    expect(server.calls.find((c) => c.url === '/api/entries')?.auth).toBeUndefined()
  })

  it('복원 중 연결이 끊겨도 앱이 멈추지 않고 로그인 화면으로 간다', async () => {
    fakeServer({
      refresh: () => {
        throw new TypeError('Failed to fetch')
      },
    })

    const result = await authGuard(to('/library'))

    expect(result).toEqual({ name: 'login', query: { redirect: '/library' } })
    expect(useAuthStore().isReady).toBe(true)
  })
})

describe('로그인 상태가 끝났을 때', () => {
  it('직접 로그아웃하면 돌아갈 주소 없이 로그인 화면으로', () => {
    expect(loginRouteAfterSessionEnd('logout', '/settings')).toEqual({ name: 'login' })
  })

  it('세션이 저절로 끝나면 보던 주소를 기억한다', () => {
    expect(loginRouteAfterSessionEnd('expired', '/library?status=BACKLOG')).toEqual({
      name: 'login',
      query: { redirect: '/library?status=BACKLOG' },
    })
  })

  it('스토어가 끝난 이유를 구분해 둔다 ─ 로그아웃은 logout, 재발급 실패는 expired', async () => {
    fakeServer({ refresh: () => json(200, { access_token: 't1' }) })
    const auth = useAuthStore()
    await auth.restore()
    await auth.logout()
    expect(auth.sessionEnd).toBe('logout')

    // 다시 로그인한 뒤 재발급까지 실패하는 상황
    fakeServer({ refresh: () => json(401, { detail: '다시 로그인해 주세요' }) })
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        if (url === '/api/auth/login') return json(200, { access_token: 't2' })
        if (url === '/api/auth/me') return json(200, ME)
        if (url === '/api/auth/refresh') return json(401, { detail: '다시 로그인해 주세요' })
        return json(401, { detail: '인증이 필요합니다' })
      }),
    )
    await auth.login('a@example.com', 'pw')
    expect(auth.sessionEnd).toBeNull()
    await request('/entries').catch(() => undefined)
    expect(auth.sessionEnd).toBe('expired')
    expect(auth.user).toBeNull()
  })
})
