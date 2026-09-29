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

// 204 ─ 돌려받을 본문이 없다 (API_SPEC 2.2절)
export function logout() {
  return request<void>('/auth/logout', { method: 'POST' })
}

export function me() {
  return request<User>('/auth/me')
}
