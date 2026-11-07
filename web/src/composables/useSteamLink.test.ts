import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useSteamLink } from './useSteamLink'
import { useAuthStore } from '@/stores/auth'
import { setAccessToken } from '@/api/client'
import type { User } from '@/api/auth'

// S-06 Steam 연결 · 동기화 · 해제 (DESIGN 3.6절)
// 다른 탭에서 연결 · 해제한 경우 · 연타 · 실패를 가짜 SERVER로 만든다

function json(status: number, body?: unknown) {
  return { ok: status >= 200 && status < 300, status, json: vi.fn().mockResolvedValue(body) } as unknown as Response
}

const LINKED: User = {
  id: 1,
  email: 'a@example.com',
  nickname: 'tester',
  created_at: '2026-10-25T00:00:00Z',
  steam_id: '76561197960287930',
  steam_synced_at: null,
  steam_persona_name: '옛 이름',
}
const UNLINKED: User = { ...LINKED, steam_id: null, steam_persona_name: null }

const SYNC_OK = {
  added: 2,
  updated: 0,
  unchanged: 0,
  skipped_manual: 1,
  skipped_limit: 0,
  skipped_no_title: 0,
  same_title_manual: 0,
  synced_at: '2026-11-07T03:00:00Z',
  steam_persona_name: '새 이름',
}

// 경로마다 답을 정하는 가짜 SERVER. 답은 함수라 부를 때마다 새로 만든다
function server(routes: Record<string, () => Response | Promise<Response>>) {
  const calls: { method: string; url: string }[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? 'GET'
      calls.push({ method, url })
      const route = routes[`${method} ${url}`]
      return route ? route() : json(404, { detail: '없음' })
    }),
  )
  return calls
}

function signedIn(user: User) {
  const auth = useAuthStore()
  auth.user = { ...user }
  return auth
}

beforeEach(() => {
  setActivePinia(createPinia())
  setAccessToken('t1')
})

afterEach(() => {
  vi.unstubAllGlobals()
  setAccessToken(null)
})

describe('연결', () => {
  it('받은 주소로 이동하고, 떠나는 동안 버튼을 다시 켜지 않는다', async () => {
    signedIn(UNLINKED)
    server({ 'POST /api/steam/link/start': () => json(200, { redirect_url: 'https://steamcommunity.com/openid/login?x=1' }) })
    const navigate = vi.fn()
    const steam = useSteamLink(navigate)

    await steam.startLink()

    expect(navigate).toHaveBeenCalledWith('https://steamcommunity.com/openid/login?x=1')
    expect(steam.busy.value).toBe('start')
  })

  it('두 번 눌러도 요청은 하나', async () => {
    signedIn(UNLINKED)
    const calls = server({ 'POST /api/steam/link/start': () => json(200, { redirect_url: 'https://steam' }) })
    const steam = useSteamLink(vi.fn())

    await Promise.all([steam.startLink(), steam.startLink()])

    expect(calls.filter((c) => c.url === '/api/steam/link/start')).toHaveLength(1)
  })

  it('409 ─ 다른 탭에서 이미 연결했다. 문구를 보이고 내 정보를 다시 받아 연결된 화면이 된다', async () => {
    const auth = signedIn(UNLINKED)
    server({
      'POST /api/steam/link/start': () => json(409, { detail: '이미 Steam 계정이 연결되어 있습니다' }),
      'GET /api/auth/me': () => json(200, LINKED),
    })
    const navigate = vi.fn()
    const steam = useSteamLink(navigate)

    await steam.startLink()

    expect(navigate).not.toHaveBeenCalled()
    expect(steam.notice.value).toEqual({ kind: 'error', text: '이미 Steam 계정이 연결되어 있습니다' })
    expect(auth.user?.steam_id).toBe(LINKED.steam_id)
    expect(steam.busy.value).toBeNull()
  })

  it('콜백 결과를 문구로, 모르는 값은 무시', () => {
    signedIn(LINKED)
    const steam = useSteamLink(vi.fn())
    steam.showCallbackResult('nope')
    expect(steam.notice.value).toBeNull()
    steam.showCallbackResult('taken')
    expect(steam.notice.value?.kind).toBe('error')
  })
})

describe('지금 동기화', () => {
  it('요약을 보이고 마지막 시각 · Steam 이름을 응답으로 바로 고친다 ─ /me를 또 부르지 않는다', async () => {
    const auth = signedIn(LINKED)
    const calls = server({ 'POST /api/steam/sync': () => json(200, SYNC_OK) })
    const steam = useSteamLink(vi.fn())

    await steam.syncNow()

    expect(steam.notice.value?.text).toBe('추가 2개 · 갱신 0개 · 변경 없음 0개')
    expect(steam.notice.value?.details?.[0]).toBe('직접 입력 1개는 그대로 뒀어요')
    expect(auth.user?.steam_synced_at).toBe(SYNC_OK.synced_at)
    expect(auth.user?.steam_persona_name).toBe('새 이름')
    expect(calls.some((c) => c.url === '/api/auth/me')).toBe(false)
    expect(steam.busy.value).toBeNull()
  })

  it('동기화 중에는 해제 · 다시 동기화가 요청을 보내지 않는다', async () => {
    signedIn(LINKED)
    let reply!: (res: Response) => void
    const calls = server({ 'POST /api/steam/sync': () => new Promise<Response>((r) => (reply = r)) })
    const steam = useSteamLink(vi.fn())

    const first = steam.syncNow()
    await steam.syncNow()
    expect(await steam.unlink()).toBe(false)
    expect(calls).toHaveLength(1)

    reply(json(200, SYNC_OK))
    await first
    expect(steam.busy.value).toBeNull()
  })

  it('비공개(409)는 서버 문구 그대로 ─ 고칠 곳이 들어 있다', async () => {
    signedIn(LINKED)
    server({
      'POST /api/steam/sync': () => json(409, { detail: "Steam 프로필의 게임 세부 정보가 비공개라 … '게임 세부 정보'를 공개로" }),
      'GET /api/auth/me': () => json(200, LINKED),
    })
    const steam = useSteamLink(vi.fn())

    await steam.syncNow()

    expect(steam.notice.value?.kind).toBe('error')
    expect(steam.notice.value?.text).toContain('공개로')
  })

  it('409 ─ 다른 탭에서 해제했다. 내 정보를 다시 받아 미연결 화면이 된다', async () => {
    const auth = signedIn(LINKED)
    server({
      'POST /api/steam/sync': () => json(409, { detail: 'Steam 계정을 먼저 연결해 주세요' }),
      'GET /api/auth/me': () => json(200, UNLINKED),
    })
    const steam = useSteamLink(vi.fn())

    await steam.syncNow()

    expect(auth.user?.steam_id).toBeNull()
  })

  it('429 · 502는 문구만, 내 정보는 그대로 · 다시 받지 않는다', async () => {
    for (const [status, detail] of [
      [429, '방금 동기화했어요. 잠시 후 다시 시도해 주세요'],
      [502, 'Steam이 응답하지 않습니다. 잠시 후 다시 시도해 주세요'],
    ] as const) {
      const auth = signedIn(LINKED)
      const calls = server({ 'POST /api/steam/sync': () => json(status, { detail }) })
      const steam = useSteamLink(vi.fn())

      await steam.syncNow()

      expect(steam.notice.value).toEqual({ kind: 'error', text: detail })
      expect(auth.user?.steam_persona_name).toBe('옛 이름')
      expect(calls.some((c) => c.url === '/api/auth/me')).toBe(false)
    }
  })

  it('프록시가 만든 504(본문이 HTML)도 문구가 있다', async () => {
    signedIn(LINKED)
    server({
      'POST /api/steam/sync': () => ({ ok: false, status: 504, json: vi.fn().mockRejectedValue(new SyntaxError()) }) as unknown as Response,
    })
    const steam = useSteamLink(vi.fn())

    await steam.syncNow()

    expect(steam.notice.value?.text).toBe('요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.')
  })
})

describe('해제', () => {
  it('성공하면 연결 정보를 비우고 기록이 남는다고 알린다', async () => {
    const auth = signedIn({ ...LINKED, steam_synced_at: SYNC_OK.synced_at })
    server({ 'DELETE /api/steam/link': () => json(204) })
    const steam = useSteamLink(vi.fn())

    expect(await steam.unlink()).toBe(true)

    expect(auth.user).toMatchObject({ steam_id: null, steam_synced_at: null, steam_persona_name: null })
    expect(steam.notice.value?.text).toContain('기록은 그대로')
  })

  it('실패하면 false ─ 대화상자 안에 이유를 보이고 연결은 그대로', async () => {
    const auth = signedIn(LINKED)
    server({})
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    const steam = useSteamLink(vi.fn())

    expect(await steam.unlink()).toBe(false)

    expect(steam.unlinkError.value).toBe('연결에 실패했습니다')
    expect(auth.user?.steam_id).toBe(LINKED.steam_id)
  })
})
