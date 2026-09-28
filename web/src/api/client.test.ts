import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { request, setAccessToken } from './client'
import { ApiError } from './errors'

// 가짜 응답을 찍어내는 틀. 진짜 서버를 띄우지 않고 원하는 상황을 만든다.
// M1의 session_factory와 같은 발상 — 상황을 기다리지 않고 테스트가 직접 만든다
function mockResponse(status: number, body?: unknown) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: vi.fn().mockResolvedValue(body),
  } as unknown as Response
}

beforeEach(() => {
  // accessToken은 모듈 안에 살아 있어서 테스트 사이에 남는다. 매번 비운다
  setAccessToken(null)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('request', () => {
  it('토큰이 없으면 Authorization 헤더를 붙이지 않는다', async () => {
    const fetchMock = vi.fn().mockResolvedValue(mockResponse(200, []))
    vi.stubGlobal('fetch', fetchMock)

    await request('/genres')

    const [, init] = fetchMock.mock.calls[0]
    expect(init.headers).not.toHaveProperty('Authorization')
  })

  it('토큰이 있으면 Bearer로 붙인다', async () => {
    const fetchMock = vi.fn().mockResolvedValue(mockResponse(200, []))
    vi.stubGlobal('fetch', fetchMock)
    setAccessToken('abc.def.ghi')

    await request('/entries')

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/entries')
    expect(init.headers.Authorization).toBe('Bearer abc.def.ghi')
  })

  it('204는 본문을 읽지 않고 undefined를 돌려준다', async () => {
    const res = mockResponse(204)
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(res))

    const result = await request('/auth/logout', { method: 'POST' })

    expect(result).toBeUndefined()
    // 가드가 실제로 막았는지 본다. json()을 부른 뒤 catch로 삼켜도 결과는 같지만,
    // 그건 다른 장치가 대신 막아준 것이지 이 줄이 일한 게 아니다
    expect(res.json).not.toHaveBeenCalled()
  })

  it('연결 자체가 실패하면 status 0인 ApiError를 던진다', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    await expect(request('/genres')).rejects.toBeInstanceOf(ApiError)
    await expect(request('/genres')).rejects.toMatchObject({
      status: 0,
      message: '연결에 실패했습니다',
    })
  })

  it('4xx는 상태 코드와 서버 문구를 담은 ApiError가 된다', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      mockResponse(404, { detail: '기록을 찾을 수 없습니다' }),
    ))

    await expect(request('/entries/999')).rejects.toMatchObject({
      status: 404,
      message: '기록을 찾을 수 없습니다',
    })
  })
})
