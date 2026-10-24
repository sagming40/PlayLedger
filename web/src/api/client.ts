import { ApiError, toApiError } from './errors'

// 모든 API는 /api로 시작한다 (API_SPEC 2장)
// 개발 → Vite / 운영 → Nginx가 이 접두사만 SERVER로 넘긴다
const BASE_URL = '/api'

// access TOKEN은 MEMORY에만 넣어둔다 (API_SPEC 3.1절)
// localStorage에 넣으면 Script가 끼어들었을 때 그대로 읽힌다
// 새로고침하면 사라지지만 의도된 동작이다 ─ refresh COOKIE로 다시 받는다 (3.3절)
let accessToken: string | null = null

// TOKEN의 주인이 바뀔 때마다(LOGIN · LOGOUT) 1씩 오르는 번호표
// 재발급이 도는 사이 LOGOUT하면, 늦게 도착한 새 TOKEN이 끝난 세션을 되살리면 안 된다
// 비유: 퇴근 처리한 직원에게 뒤늦게 도착한 출입증은 책상에 올려두지 않고 버린다
let tokenEpoch = 0

// 지금 진행 중인 재발급. 없으면 null (API_SPEC 3.2절 ③원칙)
// 동시에 401을 받은 요청들은 새로 보내지 않고 이 약속 하나를 같이 기다린다
let refreshing: Promise<boolean> | null = null

// 재발급까지 실패했을 때 부를 함수 ─ 로그인 상태를 비우는 일은 auth 스토어가 맡는다
// client.ts가 스토어 · 라우터를 직접 import하면 순환이 생기므로 등록받는다
let onAuthFailure: (() => void) | null = null

// 401이 와도 재발급하지 않는 경로 (API_SPEC 3.2절 ②원칙)
// login의 401은 자격 증명 오류, refresh의 401은 세션 만료 ─ 재발급하면 스스로를 부르는 순환이 된다
const NO_REFRESH_PATHS = new Set(['/auth/login', '/auth/refresh'])

// LOGIN · LOGOUT 시 auth 스토어에서 이 함수를 호출한다
export function setAccessToken(token: string | null) {
  accessToken = token
  tokenEpoch += 1
}

export function setAuthFailureHandler(handler: (() => void) | null) {
  onAuthFailure = handler
}

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE'
  body?: unknown
}

// SERVER에 한 번 다녀오는 것까지만 한다. 판단은 하지 않는다
async function sendOnce(path: string, options: RequestOptions, token: string | null): Promise<Response> {
  const { method = 'GET', body } = options

  const headers: Record<string, string> = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  // TOKEN이 있을 때만 붙인다. LOGIN · REGISTER는 TOKEN 없이 CALL하는 REQUESTS이다
  if (token) headers['Authorization'] = `Bearer ${token}`

  try {
    return await fetch(`${BASE_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    // SERVER가 꺼져 있거나 INTERNET이 끊긴 경우. RESPONSES 자체가 없어서 STATUS CODE도 없다
    // 0은 "HTTP RESPONSES이 아니다"라는 표시로 사용한다 (UI_DESIGN 6장 NETWORK ERROR)
    throw new ApiError(0, '연결에 실패했습니다')
  }
}

async function doRefresh(): Promise<boolean> {
  const startedAt = tokenEpoch
  // request()를 거치지 않고 직접 부른다 ─ 거치면 refresh의 401이 다시 refresh를 부를 수 있다
  const res = await sendOnce('/auth/refresh', { method: 'POST' }, null)
  const payload = await res.json().catch(() => null)

  // 기다리는 사이 LOGIN · LOGOUT이 있었다 → 이 결과는 버리고, 지금 주인의 상태를 따른다
  if (startedAt !== tokenEpoch) return accessToken !== null

  // refresh의 401 = COOKIE 없음 · 만료 · 폐기. 오류가 아니라 "로그인이 끝난 상태"다
  if (res.status === 401) {
    accessToken = null
    return false
  }
  if (!res.ok) throw toApiError(res.status, payload)

  accessToken = (payload as { access_token: string }).access_token
  return true
}

/**
 * refresh COOKIE로 access TOKEN을 새로 받는다. 성공하면 true, 로그인이 끝난 상태면 false
 *
 * 동시에 몇 번을 불러도 SERVER에는 1번만 간다 (API_SPEC 3.2절 ③원칙)
 * refresh TOKEN은 쓸 때마다 교체되므로, 같은 TOKEN으로 두 번 보내면 뒤의 것이 "폐기된 TOKEN 재사용"으로
 * 판정되어 SERVER가 이 사용자의 TOKEN을 전부 폐기한다 ─ 정상 사용자가 로그아웃된다
 * 앱 시작 시 로그인 복원(3.3절)도 이 함수를 쓴다
 */
export function refreshAccessToken(): Promise<boolean> {
  if (!refreshing) {
    refreshing = doRefresh().finally(() => {
      refreshing = null
    })
  }
  return refreshing
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  return send<T>(path, options, false)
}

async function send<T>(path: string, options: RequestOptions, retried: boolean): Promise<T> {
  // 이 요청에 실어 보낸 TOKEN을 기억한다. 401이 돌아왔을 때 이미 새 TOKEN이 있는지 비교하는 기준
  const sentToken = accessToken
  const res = await sendOnce(path, options, sentToken)

  // 204는 본문이 없다 (API_SPEC 2.2절) res.json()을 CALL하면 PARSING에서 터진다
  if (res.status === 204) return undefined as T

  // 본문이 JSON이 아닐 수도 있으므로, 실패해도 넘어간다. 판단은 아래 STATUS CODE로 한다
  const payload = await res.json().catch(() => null)

  // 401 처리 ─ 판단은 STATUS CODE와 경로로만 한다. detail 문구는 보지 않는다 (API_SPEC 3.2절 ④원칙)
  if (res.status === 401 && !NO_REFRESH_PATHS.has(path)) {
    if (!retried) {
      // 다른 요청이 그 사이 새 TOKEN을 받아왔다면 재발급 없이 바로 다시 보낸다
      // 이미 쓴 refresh COOKIE를 또 쓰지 않기 위해서다
      const renewed =
        accessToken !== null && accessToken !== sentToken ? true : await refreshAccessToken()
      // 재시도는 딱 1번 (①원칙) ─ retried=true로 넘겨 두 번째 401에서는 여기로 다시 들어오지 않는다
      if (renewed) return send<T>(path, options, true)
    }
    // 재발급 실패, 또는 새 TOKEN으로도 401 ─ 로그인 상태를 비운다
    onAuthFailure?.()
  }

  if (!res.ok) throw toApiError(res.status, payload)

  return payload as T
}
