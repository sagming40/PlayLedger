import { describe, it, expect } from 'vitest'
import { callbackNotice, formatSyncedAt, steamProfileUrl, syncNotice } from './steam-link'
import type { SteamSyncResult } from '@/api/steam'

// S-06 Steam 연동 영역의 문구 (DESIGN 3.6절)

function result(patch: Partial<SteamSyncResult> = {}): SteamSyncResult {
  return {
    added: 0,
    updated: 0,
    unchanged: 0,
    skipped_manual: 0,
    skipped_limit: 0,
    skipped_no_title: 0,
    same_title_manual: 0,
    synced_at: '2026-11-07T03:00:00Z',
    steam_persona_name: null,
    ...patch,
  }
}

describe('콜백 결과', () => {
  it('서버가 보내는 다섯 값은 문구가 있다 ─ linked만 성공', () => {
    expect(callbackNotice('linked')?.kind).toBe('success')
    for (const value of ['taken', 'already', 'unavailable', 'failed']) {
      expect(callbackNotice(value)?.kind).toBe('error')
    }
  })

  it('모르는 값 · 배열 · 없음은 아무것도 보이지 않는다 ─ 주소를 고쳐 쓴 것', () => {
    expect(callbackNotice('hacked')).toBeNull()
    expect(callbackNotice('toString')).toBeNull() // 객체의 상속 이름에 걸리지 않는다
    expect(callbackNotice(['linked', 'taken'])).toBeNull()
    expect(callbackNotice(undefined)).toBeNull()
  })
})

describe('동기화 요약', () => {
  it('세 숫자는 0이어도 보인다 ─ "아무것도 안 바뀜"도 알려 준다', () => {
    const notice = syncNotice(result({ unchanged: 17 }))
    expect(notice.text).toBe('추가 0개 · 갱신 0개 · 변경 없음 17개')
    expect(notice.details).toEqual([])
  })

  it('덧붙임 줄은 0이 아닌 것만, 큰 수는 자릿수 쉼표', () => {
    const notice = syncNotice(result({ added: 1200, skipped_manual: 1, same_title_manual: 2, skipped_limit: 30, skipped_no_title: 4 }))
    expect(notice.text).toBe('추가 1,200개 · 갱신 0개 · 변경 없음 0개')
    expect(notice.details).toEqual([
      '직접 입력 1개는 그대로 뒀어요',
      '같은 제목의 직접 등록 게임 2개가 있어요 ─ 두 번 세어질 수 있어요',
      '기록이 5,000개를 넘어 30개는 가져오지 못했어요',
      '이름을 읽을 수 없는 게임 4개는 건너뛰었어요',
      '새로 들어온 게임은 당분간 영어 이름 · 기본 커버로 보여요',
    ])
  })

  it('새로 들어온 게임이 없으면 영어 이름 안내도 없다', () => {
    expect(syncNotice(result({ updated: 3 })).details).toEqual([])
  })
})

describe('마지막 동기화 시각', () => {
  // 이 기기 시간으로 만든다 ─ 테스트가 어느 시간대에서 돌아도 같다
  const now = new Date(2026, 10, 7, 15, 30)

  it('없으면 아직', () => {
    expect(formatSyncedAt(null, now)).toBe('아직 동기화하지 않았어요')
    expect(formatSyncedAt('이상한 값', now)).toBe('아직 동기화하지 않았어요')
  })

  it('1분 안 · 미래(기기 시계가 느림)는 방금, 1시간 안은 분', () => {
    expect(formatSyncedAt(new Date(2026, 10, 7, 15, 29, 30).toISOString(), now)).toBe('방금 전')
    expect(formatSyncedAt(new Date(2026, 10, 7, 15, 31).toISOString(), now)).toBe('방금 전')
    expect(formatSyncedAt(new Date(2026, 10, 7, 15, 5).toISOString(), now)).toBe('25분 전')
  })

  it('같은 날은 오늘 시각, 다른 날은 날짜까지', () => {
    expect(formatSyncedAt(new Date(2026, 10, 7, 9, 5).toISOString(), now)).toBe('오늘 09:05')
    expect(formatSyncedAt(new Date(2026, 10, 6, 23, 59).toISOString(), now)).toBe('2026-11-06 23:59')
  })

  it('UTC 시각(...Z)을 이 기기 시간으로 읽는다 ─ 날짜만 있는 값처럼 하루가 밀리지 않는다', () => {
    const iso = '2026-11-06T15:00:00Z'
    const at = new Date(iso)
    const pad = (v: number) => String(v).padStart(2, '0')
    const later = new Date(at.getTime() + 2 * 24 * 60 * 60_000)
    expect(formatSyncedAt(iso, later)).toBe(
      `${at.getFullYear()}-${pad(at.getMonth() + 1)}-${pad(at.getDate())} ${pad(at.getHours())}:${pad(at.getMinutes())}`,
    )
  })
})

it('Steam 프로필 주소', () => {
  expect(steamProfileUrl('76561197960287930')).toBe('https://steamcommunity.com/profiles/76561197960287930')
})
