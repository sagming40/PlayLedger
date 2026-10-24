import { describe, it, expect, vi, beforeEach, afterEach, type Mock } from 'vitest'
import { request, refreshAccessToken, setAccessToken, setAuthFailureHandler } from './client'
import { ApiError } from './errors'

// API_SPEC 3.2절 401 처리 4원칙 + 설계 검증에서 찾은 경쟁 상황 2가지
// 토큰 만료 · 동시 재발급은 브라우저에서 손으로 만들 수 없는 상황이라 여기서만 검증한다

function json(status: number, body?: unknown) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: vi.fn().mockResolvedValue(body),
  } as unknown as Response
}

// 나중에 테스트가 직접 풀어주는 약속 ─ "응답이 아직 안 온 상태"를 만든다
function deferred<T>() {
  let resolve!: (v: T) => void
  let reject!: (e: unknown) => void
  const promise = new Promise<T>((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

interface Call {
  url: string
  auth?: string
}

// 가짜 SERVER ─ 어떤 access TOKEN이 유효한지, refresh가 어떻게 답할지를 테스트가 정한다
function fakeServer(opts: { valid: string[]; refresh: () => Response | Promise<Response> }) {
  const calls: Call[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init: RequestInit) => {
      const auth = (init.headers as Record<string, string>)['Authorization']
      calls.push({ url, auth })
      if (url === '/api/auth/refresh') return opts.refresh()
      if (url === '/api/auth/login') return json(401, { detail: '이메일 또는 비밀번호가 올바르지 않습니다' })
      const token = auth?.replace('Bearer ', '')
      if (token && opts.valid.includes(token)) return json(200, { path: url })
      return json(401, { detail: '인증이 필요합니다' })
    }),
  )
  return {
    calls,
    refreshCount: () => calls.filter((c) => c.url === '/api/auth/refresh').length,
  }
}

let onFailure: Mock<() => void>

beforeEach(() => {
  // TOKEN · 실패 처리기는 모듈 안에 살아 있어서 테스트 사이에 남는다. 매번 초기화
  setAccessToken(null)
  onFailure = vi.fn<() => void>()
  setAuthFailureHandler(onFailure)
})

afterEach(() => {
  setAuthFailureHandler(null)
  vi.unstubAllGlobals()
})

describe('401 처리 4원칙 (API_SPEC 3.2절)', () => {
  it('만료된 TOKEN이면 재발급 후 새 TOKEN으로 원래 요청을 다시 보낸다', async () => {
    const server = fakeServer({ valid: ['new'], refresh: () => json(200, { access_token: 'new' }) })
    setAccessToken('old')

    const result = await request('/entries')

    expect(result).toEqual({ path: '/api/entries' })
    expect(server.refreshCount()).toBe(1)
    expect(server.calls.at(-1)).toEqual({ url: '/api/entries', auth: 'Bearer new' })
    expect(onFailure).not.toHaveBeenCalled()
  })

  it('① 재시도에서도 401이면 더 재발급하지 않고 로그인 상태를 비운다', async () => {
    // 재발급은 되지만 새 TOKEN도 거절당하는 상황 (예: 그 사이 계정 삭제)
    const server = fakeServer({ valid: [], refresh: () => json(200, { access_token: 'new' }) })
    setAccessToken('old')

    await expect(request('/entries')).rejects.toMatchObject({ status: 401 })
    expect(server.refreshCount()).toBe(1)
    expect(onFailure).toHaveBeenCalledTimes(1)
  })

  it('② 로그인 API의 401은 재발급하지 않고 문구를 그대로 돌려준다', async () => {
    const server = fakeServer({ valid: [], refresh: () => json(200, { access_token: 'new' }) })

    await expect(request('/auth/login', { method: 'POST', body: {} })).rejects.toMatchObject({
      status: 401,
      message: '이메일 또는 비밀번호가 올바르지 않습니다',
    })
    expect(server.refreshCount()).toBe(0)
    // 로그인 실패는 "로그인 상태가 끝남"이 아니다 ─ 화면은 폼 아래 문구만 띄운다
    expect(onFailure).not.toHaveBeenCalled()
  })

  it('③ 동시에 401을 받은 요청이 여럿이어도 재발급은 1번만 보낸다', async () => {
    const gate = deferred<Response>()
    const server = fakeServer({ valid: ['new'], refresh: () => gate.promise })
    setAccessToken('old')

    const all = Promise.all([request('/entries'), request('/genres'), request('/auth/me')])
    // 세 요청이 모두 401을 받고 재발급을 기다리는 상태까지 진행시킨다
    await new Promise((r) => setTimeout(r, 0))
    gate.resolve(json(200, { access_token: 'new' }))

    const results = await all
    expect(results).toHaveLength(3)
    expect(server.refreshCount()).toBe(1)
  })

  it('④ 분기는 상태 코드로만 한다 ─ 문구가 달라도 401이면 재발급, 같은 문구라도 403이면 하지 않는다', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(json(401, { detail: '처음 보는 문구' }))
      .mockResolvedValueOnce(json(200, { access_token: 'new' }))
      .mockResolvedValueOnce(json(200, { ok: true }))
      .mockResolvedValueOnce(json(403, { detail: '인증이 필요합니다' }))
    vi.stubGlobal('fetch', fetchMock)
    setAccessToken('old')

    await expect(request('/entries')).resolves.toEqual({ ok: true })
    await expect(request('/entries')).rejects.toMatchObject({ status: 403 })

    const refreshCalls = fetchMock.mock.calls.filter(([url]) => url === '/api/auth/refresh')
    expect(refreshCalls).toHaveLength(1)
  })
})

describe('재발급 실패 · 경쟁 상황', () => {
  it('재발급이 401이면 TOKEN을 비우고 로그인 상태를 비운다', async () => {
    const server = fakeServer({ valid: [], refresh: () => json(401, { detail: '다시 로그인해 주세요' }) })
    setAccessToken('old')

    await expect(request('/entries')).rejects.toMatchObject({ status: 401 })
    expect(onFailure).toHaveBeenCalledTimes(1)

    // 비운 뒤의 요청에는 Authorization이 붙지 않는다
    await request('/entries').catch(() => undefined)
    expect(server.calls.find((c, i) => i > 1 && c.url === '/api/entries')?.auth).toBeUndefined()
  })

  it('재발급 중 연결이 끊기면 연결 오류로 끝내고 로그아웃시키지 않는다', async () => {
    fakeServer({
      valid: [],
      refresh: () => {
        throw new TypeError('Failed to fetch')
      },
    })
    setAccessToken('old')

    const err = await request('/entries').catch((e) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect(err).toMatchObject({ status: 0 })
    expect(onFailure).not.toHaveBeenCalled()
  })

  it('다른 요청이 이미 새 TOKEN을 받아온 뒤 도착한 401은 재발급 없이 바로 다시 보낸다', async () => {
    const late = deferred<Response>()
    const calls: Call[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init: RequestInit) => {
        const auth = (init.headers as Record<string, string>)['Authorization']
        calls.push({ url, auth })
        if (url === '/api/auth/refresh') return json(200, { access_token: 'new' })
        // 옛 TOKEN으로 보낸 첫 요청만 응답이 늦게 온다
        if (auth === 'Bearer old') return late.promise
        return json(200, { ok: true })
      }),
    )
    setAccessToken('old')

    const slow = request('/entries')
    await new Promise((r) => setTimeout(r, 0))
    // 그 사이 다른 경로(예: 다른 요청의 401)로 재발급이 끝났다
    await refreshAccessToken()
    late.resolve(json(401, { detail: '인증이 필요합니다' }))

    await expect(slow).resolves.toEqual({ ok: true })
    // 재발급은 위에서 직접 부른 1번뿐 ─ 이미 쓴 refresh COOKIE를 또 쓰지 않았다
    expect(calls.filter((c) => c.url === '/api/auth/refresh')).toHaveLength(1)
    expect(calls.at(-1)).toEqual({ url: '/api/entries', auth: 'Bearer new' })
  })

  it('재발급이 도는 사이 로그아웃하면, 늦게 온 새 TOKEN으로 세션을 되살리지 않는다', async () => {
    const gate = deferred<Response>()
    let refreshCalls = 0
    // 첫 재발급은 응답이 늦게 오고, 그 뒤로는 로그아웃으로 COOKIE가 폐기된 상태(401)
    const server = fakeServer({
      valid: ['new'],
      refresh: () => (++refreshCalls === 1 ? gate.promise : json(401, { detail: '다시 로그인해 주세요' })),
    })
    setAccessToken('old')

    const pending = request('/entries')
    await new Promise((r) => setTimeout(r, 0))
    setAccessToken(null) // 로그아웃 (auth 스토어의 logout이 하는 일)
    gate.resolve(json(200, { access_token: 'new' }))

    await expect(pending).rejects.toMatchObject({ status: 401 })

    // 늦게 온 'new'는 버려졌다 ─ 이후 요청을 포함해 어떤 요청에도 실려 나가지 않는다
    await request('/entries').catch(() => undefined)
    expect(server.calls.some((c) => c.auth === 'Bearer new')).toBe(false)
  })
})
