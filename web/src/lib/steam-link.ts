// S-06 Steam 연동 영역의 문구 (DESIGN 3.6절)
// 화면 없이 테스트할 수 있게 계산만 여기 둔다 ─ 상태와 요청은 composables/useSteamLink.ts

import type { SteamSyncResult } from '@/api/steam'

export interface SteamNotice {
  kind: 'success' | 'error'
  text: string
  // 요약 아래에 덧붙이는 줄 ─ 건너뛴 것 · 주의할 것
  details?: string[]
}

// 콜백이 /settings?steam= 로 알려 주는 결과 (server/app/routers/steam_link.py link_callback)
const CALLBACK_NOTICES: Record<string, SteamNotice> = {
  linked: { kind: 'success', text: 'Steam 계정을 연결했어요. 지금 동기화를 누르면 라이브러리를 가져와요.' },
  taken: { kind: 'error', text: '이 Steam 계정은 다른 PlayLedger 계정에 이미 연결되어 있어요.' },
  already: { kind: 'error', text: '이미 다른 Steam 계정이 연결되어 있어요. 연결을 해제한 뒤 다시 시도해 주세요.' },
  unavailable: { kind: 'error', text: 'Steam이 응답하지 않아 연결하지 못했어요. 잠시 후 다시 시도해 주세요.' },
  // 위조 · 만료(5분) · 다른 브라우저에서 돌아옴 ─ 사용자가 할 수 있는 일은 "다시"뿐이라 하나로 묶는다 (ARCHITECTURE 3.10절)
  failed: { kind: 'error', text: 'Steam 연결을 확인하지 못했어요. Steam 로그인은 5분 안에 마쳐야 해요. 다시 시도해 주세요.' },
}

/**
 * 주소의 steam= 값을 문구로 바꾼다. 모르는 값이면 null ─ 누가 주소를 고쳐 쓴 것이라 아무것도 보이지 않는다
 * 배열(?steam=a&steam=b)도 그렇게 본다
 */
export function callbackNotice(value: unknown): SteamNotice | null {
  if (typeof value !== 'string' || !Object.hasOwn(CALLBACK_NOTICES, value)) return null
  return CALLBACK_NOTICES[value]!
}

/**
 * 동기화 결과 요약 (DESIGN 3.6절 "동기화 결과 표시")
 * "완료되었습니다"만 뜨면 뭐가 바뀌었는지 알 수 없다 ─ 숫자를 보인다. 0인 덧붙임 줄은 뺀다
 */
export function syncNotice(result: SteamSyncResult): SteamNotice {
  const n = (count: number) => count.toLocaleString('ko-KR')
  const details: string[] = []
  if (result.skipped_manual > 0) details.push(`직접 입력 ${n(result.skipped_manual)}개는 그대로 뒀어요`)
  if (result.same_title_manual > 0)
    details.push(`같은 제목의 직접 등록 게임 ${n(result.same_title_manual)}개가 있어요 ─ 두 번 세어질 수 있어요`)
  if (result.skipped_limit > 0) details.push(`기록이 5,000개를 넘어 ${n(result.skipped_limit)}개는 가져오지 못했어요`)
  if (result.skipped_no_title > 0) details.push(`이름을 읽을 수 없는 게임 ${n(result.skipped_no_title)}개는 건너뛰었어요`)
  // 상세(한국어 이름 · 커버)는 아직 받지 않는다 (decisions/0016). 채우기를 구현하면 "차례로 채워져요"로 바꾼다 (PLAN M6)
  if (result.added > 0) details.push('새로 들어온 게임은 당분간 영어 이름 · 기본 커버로 보여요')
  return {
    kind: 'success',
    text: `추가 ${n(result.added)}개 · 갱신 ${n(result.updated)}개 · 변경 없음 ${n(result.unchanged)}개`,
    details,
  }
}

/**
 * 마지막 동기화 시각. synced_at은 UTC 시각(...Z)이라 Date로 읽어 이 기기의 시간으로 보인다
 * (날짜만 있는 purchased_at과 다르다 ─ CLAUDE.md 함정 "날짜와 시각")
 */
export function formatSyncedAt(iso: string | null, now: Date = new Date()): string {
  if (iso === null) return '아직 동기화하지 않았어요'
  const at = new Date(iso)
  if (Number.isNaN(at.getTime())) return '아직 동기화하지 않았어요'
  const minutes = Math.floor((now.getTime() - at.getTime()) / 60_000)
  // 기기 시계가 조금 느려 미래로 보여도 "방금"
  if (minutes < 1) return '방금 전'
  if (minutes < 60) return `${minutes}분 전`
  const pad = (v: number) => String(v).padStart(2, '0')
  const time = `${pad(at.getHours())}:${pad(at.getMinutes())}`
  const sameDay = at.getFullYear() === now.getFullYear() && at.getMonth() === now.getMonth() && at.getDate() === now.getDate()
  if (sameDay) return `오늘 ${time}`
  return `${at.getFullYear()}-${pad(at.getMonth() + 1)}-${pad(at.getDate())} ${time}`
}

/** Steam 프로필 주소. steam_id는 서버가 17자리 숫자만 받는다 (ARCHITECTURE 5.4절) */
export function steamProfileUrl(steamId: string): string {
  return `https://steamcommunity.com/profiles/${encodeURIComponent(steamId)}`
}
