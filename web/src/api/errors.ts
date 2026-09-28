// 422 Array의 한 항목에서 사용할 것들만 추려낸 모양 (API_SPEC 4.4절)
export interface FieldIssue {
  field: string                   // 어느 입력칸인지 ('email', 'password')
  rule: string                    // 무슨 규칙을 어겼는지 ('string_too_short')
  ctx?: Record<string, unknown>   // 규칙의 기준값. 존재하지 않는 오류도 있다
}

// SERVER 4xx · 5xx로 답했을 때 던지는 오류
// status를 들고 다니는 이유는, 호출하는 쪽이 "401이면 로그인으로" 처럼
// 상태 코드로만 분기하기 위함이다 (API_SPEC 3.2절 ④원칙 ─ 문구로 분기하지 않는다)
export class ApiError extends Error {
  readonly status: number
  readonly issues: FieldIssue[]

  constructor(status: number, message: string, issues: FieldIssue[] = []) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.issues = issues
  }
}

// 500의 detail은 FastAPI default라 영문이다. 화면에는 이 문장을 대신 사용한다
const FALLBACK_MESSAGE = '요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.'

// 응답 본문을 보고 알맞은 ApiError를 만들어준다
// 동일한 detail 키에 문자열이 오기도 하고 배열이 오기도 해서 분기가 필요하다
export function toApiError(status: number, body: unknown): ApiError {
  const detail = (body as { detail?: unknown } | null)?.detail

  // ① 문자열 ─ SERVER가 한국어로 써준 문장. 그대로 화면에 사용할 수 있다 (API_SPEC 2.3절)
  if (typeof detail === 'string') {
    if (status >= 500) return new ApiError(status, FALLBACK_MESSAGE)
    return new ApiError(status, detail)
  }

  // ② 배열 ─ Pydantic이 만든 422 (API_SPEC 4.4절)
  // msg는 영문이기 때문에 화면에 띄우지 못한다. 어느 칸에서 무슨 규칙이 깨졌는지만 뽑아둔다
  if (Array.isArray(detail)) {
    const issues: FieldIssue[] = detail.map((item) => {
      const raw = item as { loc?: unknown[]; type?: string; ctx?: Record<string, unknown> }
      // loc은 ["body", "password"]처럼 경로이다. 마지막 칸이 입력란 이름
      const loc = Array.isArray(raw.loc) ? raw.loc : []
      return {
        field: String(loc[loc.length - 1] ?? ''),
        rule: raw.type ?? 'unknown',
        ctx: raw.ctx,
      }
    })
    return new ApiError(status, '입력한 내용을 다시 확인해 주세요', issues)
  }

  // ③ 그 외 ─ JSON이 아니거나 모양이 다르다
  return new ApiError(status, FALLBACK_MESSAGE)
}
