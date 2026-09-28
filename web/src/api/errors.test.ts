import { describe, it, expect } from 'vitest'
import { toApiError } from './errors'

describe('toApiError', () => {
  it('detail이 문자열이면 그대로 화면 문구로 사용한다', () => {
    const err = toApiError(409, { detail: '이미 등록된 게임입니다' })
    expect(err.status).toBe(409)
    expect(err.message).toBe('이미 등록된 게임입니다')
    expect(err.issues).toEqual([])
  })

  it('500은 detail이 영문이므로 고정 문구로 바꾼다', () => {
    const err = toApiError(500, { detail: 'Internal Server Error' })
    expect(err.message).not.toContain('Internal')
  })

  it('422 배열에서 입력칸과 규칙만 뽑아낸다', () => {
    // API_SPEC 4.4절의 실제 응답 예시를 그대로 옮김
    const err = toApiError(422, {
      detail: [
        {
          type: 'string_too_short',
          loc: ['body', 'password'],
          msg: 'String should have at least 8 characters',
          input: '123',
          ctx: { min_length: 8 },
        },
      ],
    })
    expect(err.issues).toEqual([
      { field: 'password', rule: 'string_too_short', ctx: { min_length: 8 } },
    ])
    // 배열을 그대로 문장에 넣으면 화면에 [object Object]가 뜬다
    expect(err.message).not.toContain('object')
  })

  it('ctx가 없는 오류도 처리한다', () => {
    // missing 처럼 기준값이 없는 오류엔 ctx가 붙지 않는다
    const err = toApiError(422, {
      detail: [{ type: 'missing', loc: ['body', 'email'], msg: 'Field required' }],
    })
    expect(err.issues[0]).toEqual({ field: 'email', rule: 'missing', ctx: undefined })
  })

  it('본문이 없거나 모양이 달라도 터지지 않는다', () => {
    expect(() => toApiError(502, null)).not.toThrow()
    expect(toApiError(502, null).status).toBe(502)
    expect(toApiError(502, '응답이 JSON이 아님').issues).toEqual([])
  })
})
