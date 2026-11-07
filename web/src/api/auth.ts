import { request } from './client'

// SERVER가 돌려주는 모양 ─ 실제 응답과 맞는지는 Swagger에서 확인
export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface User {
  id: number
  email: string
  nickname: string
  created_at: string
  // S-06 Steam 연동 영역 (server/app/schemas/user.py UserRead). 연결 안 했으면 셋 다 null
  steam_id: string | null
  steam_synced_at: string | null // UTC 시각 ─ ...Z (시각 파서로 읽는다)
  steam_persona_name: string | null // 못 받았으면 null ─ 화면은 "Steam 계정 연결됨"으로 보인다
}

// 아래 4개 함수는 "주문서 양식"이다
// 실제로 SERVER에 다녀오는 일(헤더 붙이기·에러 변환)은 전부 client.ts의 request 담당
// 비유: 메뉴판 / request ─ 주방

export function login(email: string, password: string) {
  return request<TokenResponse>('/auth/login', {
    method: 'POST',
    body: { email, password },
  })
}

export function register(email: string, password: string, nickname: string) {
  return request<User>('/auth/register', {
    method: 'POST',
    body: { email, password, nickname },
  })
}

// 204 ─ 돌려받을 본문이 없다 (ARCHITECTURE 3.1절)
export function logout() {
  return request<void>('/auth/logout', { method: 'POST' })
}

export function me() {
  return request<User>('/auth/me')
}

// 비밀번호를 한 번 더 받는다 (S-06). 204 ─ 돌려받을 본문이 없다
export function deleteAccount(password: string) {
  return request<void>('/auth/me', { method: 'DELETE', body: { password } })
}
