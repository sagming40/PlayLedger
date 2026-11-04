import { describe, it, expect } from 'vitest'
import { toApiError } from './errors'

describe('toApiError', () => {
  it('detail이 문자열이면 그대로 화면 문구로 사용한다', () => {
    const err = toApiError(409, { detail: '이미 등록된 게임입니다' })
    expect(err.status).toBe(409)
    expect(err.message).toBe('이미 등록된 게임입니다')
    expect(err.issues).toEqual([])
  })

  it('500도 서버의 한국어 문장을 그대로 쓴다', () => {
    const err = toApiError(500, { detail: '서버에 문제가 생겼습니다. 잠시 후 다시 시도해 주세요' })
    expect(err.message).toContain('서버에 문제가')
  })

  it('프록시가 만든 502처럼 detail이 없으면 고정 문구', () => {
    expect(toApiError(502, null).message).toContain('잠시 후')
  })

  it('422 배열에서 입력칸과 규칙만 뽑아낸다', () => {
    // ARCHITECTURE 3.9절의 실제 응답 예시를 그대로 옮김
    const err = toApiError(422, {
      detail: [
        {
          type: 'string_too_short',
          loc: ['body', 'password'],
          msg: 'String should have at least 8 characters',
        },
      ],
    })
    expect(err.issues).toEqual([{ field: 'password', rule: 'string_too_short' }])
    // 배열을 그대로 문장에 넣으면 화면에 [object Object]가 뜬다
    expect(err.message).not.toContain('object')
  })

  it('본문이 없거나 모양이 달라도 터지지 않는다', () => {
    expect(() => toApiError(502, null)).not.toThrow()
    expect(toApiError(502, null).status).toBe(502)
    expect(toApiError(502, '응답이 JSON이 아님').issues).toEqual([])
  })
})
