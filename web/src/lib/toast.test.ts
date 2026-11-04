import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { showToast, toast } from './toast'

// 저장 성공 알림 (DESIGN 6장) ─ 시간이 흐르는 일이라 가짜 시계로 본다

beforeEach(() => {
  vi.useFakeTimers()
  toast.value = null
})

afterEach(() => {
  vi.useRealTimers()
})

describe('저장 성공 알림', () => {
  it('보였다가 시간이 지나면 사라진다', () => {
    showToast('저장했어요')
    expect(toast.value?.text).toBe('저장했어요')
    vi.advanceTimersByTime(2499)
    expect(toast.value).not.toBeNull()
    vi.advanceTimersByTime(1)
    expect(toast.value).toBeNull()
  })

  it('새 알림이 앞 알림을 바꾸고, 앞 알림의 시계가 새 알림을 지우지 않는다', () => {
    showToast('저장했어요')
    vi.advanceTimersByTime(2000)
    showToast('삭제했어요')
    expect(toast.value?.text).toBe('삭제했어요')
    vi.advanceTimersByTime(2000)
    expect(toast.value?.text).toBe('삭제했어요')
    vi.advanceTimersByTime(500)
    expect(toast.value).toBeNull()
  })

  it('같은 문구가 또 떠도 새 알림이다 ─ 다시 움직이고 시간도 새로 잰다', () => {
    showToast('저장했어요')
    const first = toast.value!.id
    vi.advanceTimersByTime(2000)
    showToast('저장했어요')
    expect(toast.value!.id).not.toBe(first)
    vi.advanceTimersByTime(2000)
    expect(toast.value).not.toBeNull()
  })
})
