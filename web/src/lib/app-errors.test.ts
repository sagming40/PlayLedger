import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { appError, handleAppError, isChunkLoadError, reloadOnce } from './app-errors'

// 시험은 Node에서 돈다 ─ 브라우저 저장소를 흉내 낸다
function fakeStorage() {
  const data = new Map<string, string>()
  return {
    getItem: (key: string) => data.get(key) ?? null,
    setItem: (key: string, value: string) => void data.set(key, value),
  }
}

beforeEach(() => vi.stubGlobal('sessionStorage', fakeStorage()))
afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('isChunkLoadError', () => {
  it.each([
    'Failed to fetch dynamically imported module: https://x/assets/a.js',
    'error loading dynamically imported module',
    'Importing a module script failed.',
    'Loading chunk 12 failed',
  ])('화면 조각 실패: %s', (message) => {
    expect(isChunkLoadError(new Error(message))).toBe(true)
  })

  it('다른 오류는 아니다', () => {
    expect(isChunkLoadError(new TypeError('x is not a function'))).toBe(false)
  })
})

describe('reloadOnce', () => {
  it('처음에는 새로고침하고, 바로 또 실패하면 하지 않는다 ─ 무한 반복 방지', () => {
    const reload = vi.fn()
    expect(reloadOnce(reload, 100_000)).toBe(true)
    expect(reloadOnce(reload, 110_000)).toBe(false)
    expect(reload).toHaveBeenCalledTimes(1)
  })

  it('시간이 지나면 다시 할 수 있다 ─ 다음 배포', () => {
    const reload = vi.fn()
    reloadOnce(reload, 100_000)
    expect(reloadOnce(reload, 200_000)).toBe(true)
  })

  it('저장소를 못 쓰면 하지 않는다 ─ 횟수를 셀 수 없다', () => {
    vi.stubGlobal('sessionStorage', {
      getItem: () => {
        throw new Error('blocked')
      },
    })
    const reload = vi.fn()
    expect(reloadOnce(reload)).toBe(false)
    expect(reload).not.toHaveBeenCalled()
  })
})

describe('handleAppError', () => {
  beforeEach(() => {
    appError.value = null
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  it('일반 오류는 띠로 알린다', () => {
    handleAppError(new TypeError('boom'))
    expect(appError.value).toContain('새로고침')
  })

  it('오프라인이면 새로고침하지 않는다 ─ 지금 화면까지 브라우저 오류 페이지가 된다', () => {
    vi.stubGlobal('navigator', { onLine: false })
    const assign = vi.fn()
    vi.stubGlobal('window', { location: { assign, reload: assign } })
    handleAppError(new Error('Failed to fetch dynamically imported module'), '/login')
    expect(assign).not.toHaveBeenCalled()
    expect(appError.value).toContain('인터넷 연결')
  })

  it('온라인의 첫 조각 실패는 가려던 주소로 새로 연다 ─ 새 버전 배포 직후', () => {
    vi.stubGlobal('navigator', { onLine: true })
    const assign = vi.fn()
    vi.stubGlobal('window', { location: { assign, reload: vi.fn() } })
    handleAppError(new Error('Failed to fetch dynamically imported module'), '/stats')
    expect(assign).toHaveBeenCalledWith('/stats')
    expect(appError.value).toBeNull()
  })

  it('두 번째 조각 실패도 빈 화면이 아니라 띠로 알린다', () => {
    sessionStorage.setItem('pl-chunk-reload', String(Date.now()))
    handleAppError(new Error('Failed to fetch dynamically imported module'))
    expect(appError.value).toContain('새로고침')
  })
})
