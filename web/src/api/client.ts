import { ApiError, toApiError } from './errors'

// 모든 API는 /api로 시작한다 (API_SPEC 2장)
// 개발 → Vite / 운영 → Nginx가 이 접두사만 SERVER로 넘긴다
const BASE_URL = '/api'

// access TOKEN은 MEMORY에만 넣어둔다 (API_SPEC 3.1절)
// localStorage에 넣으면 Script가 끼어들었을 때 그대로 읽힌다
// 새로고침하면 사라지지만 의도된 동작이다 ─ refresh COOKIE로 다시 받는다 (3.3절)
let accessToken: string | null = null

// LOGIN · 재발급 · LOGOUT 시 auth 스토어에서 이 함수를 호출한다
export function setAccessToken(token: string | null) {
  accessToken = token
}

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE'
  body?: unknown
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body } = options

  const headers: Record<string, string> = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  // TOKEN이 있을 때만 붙인다. LOGIN · REGISTER는 TOKEN 없이 CALL하는 REQUESTS이다
  if (accessToken) headers['Authorization'] = `Bearer ${accessToken}`

  let res: Response
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    // SERVER가 꺼져 있거나 INTERNET이 끊긴 경우. RESPONSES 자체가 없어서 STATUS CODE도 없다
    // 0은 "HTTP RESPONSES이 아니다"라는 표시로 사용한다 (UI_DESIGN 6장 NETWORK ERROR)
    throw new ApiError(0, '연결에 실패했습니다')
  }

  // 204는 본문이 없다 (API_SPEC 2.2절) res.json()을 CALL하면 PARSING에서 터진다
  if (res.status === 204) return undefined as T

  // 본문이 JSON이 아닐 수도 있으므로, 실패해도 넘어간다. 판단은 아래 STATUS CODE로 한다
  const payload = await res.json().catch(() => null)

  if (!res.ok) throw toApiError(res.status, payload)

  return payload as T
}
