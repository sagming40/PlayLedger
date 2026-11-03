import { ref } from 'vue'
import { getEntry, updateEntry, type Entry, type EntryStatus } from '@/api/entries'
import { ApiError } from '@/api/errors'

// 네트워크가 끊겨 SERVER 답 자체가 없을 때 (DESIGN 6장)
export const OFFLINE_MESSAGE = '연결에 실패했습니다'

// 상세 화면에서 수정 화면을 거치지 않고 바로 고치는 값
export type QuickEdit = Partial<Pick<Entry, 'status' | 'rating' | 'review'>>

/**
 * S-04 게임 상세의 기록 하나와 바로 고치기(상태 · 평점 · 한줄평) (DESIGN 3.4 · 4.3 · 6장)
 *
 * useEntryList처럼 화면이 그때그때 만든다 ─ 다른 계정으로 바꿔 로그인해도 앞 계정의 기록이 남지 않는다
 */
export function useEntryDetail() {
  const entry = ref<Entry | null>(null)
  const loading = ref(false)
  const loadError = ref<string | null>(null)
  // 없거나 남의 기록 ─ SERVER가 둘을 같은 404로 답한다 (ARCHITECTURE 3.8절). 화면도 같은 문구 하나로 보여준다
  const notFound = ref(false)

  const saving = ref(false)
  const saveError = ref<string | null>(null)
  // 어느 칸의 저장이 실패했는지 ─ 실패 문구를 그 칸 옆에 보여 준다
  const failedField = ref<keyof QuickEdit | null>(null)

  // 마지막으로 부른 load의 번호 ─ 상세에서 상세로 빠르게 옮겨 다니면 앞 게임의 답이 늦게 와서 덮어쓸 수 있다
  // 번호표를 뽑아 두고, 답이 왔을 때 내 번호가 최신이 아니면 버린다
  let loadSeq = 0

  function message(e: unknown) {
    return e instanceof ApiError ? e.message : OFFLINE_MESSAGE
  }

  async function load(id: number) {
    const seq = ++loadSeq
    loading.value = true
    loadError.value = null
    notFound.value = false
    saveError.value = null
    failedField.value = null
    // 다른 게임으로 옮겼으면 앞 게임을 지운다 ─ 남겨 두면 잠깐 동안 엉뚱한 게임이 보인다
    if (entry.value?.id !== id) entry.value = null
    try {
      const found = await getEntry(id)
      if (seq !== loadSeq) return
      entry.value = found
    } catch (e) {
      if (seq !== loadSeq) return
      if (e instanceof ApiError && e.status === 404) notFound.value = true
      else loadError.value = message(e)
    } finally {
      if (seq === loadSeq) loading.value = false
    }
  }

  /**
   * 상세 화면에서 바로 고치는 값 ─ 상태 · 평점 · 한줄평 (DESIGN 3.4 · 4.3절)
   *
   * 고른 값을 먼저 화면에 반영하고(점 색 · 평점 칸 · 별이 바로 바뀐다), 실패하면 원래 값으로 되돌린다
   * 저장 중에는 다른 값도 바꿀 수 없다 ─ 두 요청이 거꾸로 도착하면 화면과 DB가 다른 상태가 된다 (DESIGN 6장 중복 제출 차단)
   * 보낸 항목만 바뀐다(PATCH). 상태를 바꿀 때 평점 · 한줄평은 보내지 않아 숨기기만 한다 (DESIGN 4.3절)
   * 저장에 성공하면 true ─ 한줄평 입력칸은 성공했을 때만 닫는다
   */
  async function save(changes: QuickEdit): Promise<boolean> {
    const current = entry.value
    if (!current || saving.value) return false
    const keys = Object.keys(changes) as (keyof QuickEdit)[]
    // 바뀌는 게 없으면 요청하지 않는다
    if (keys.every((k) => current[k] === changes[k])) return true
    const previous = Object.fromEntries(keys.map((k) => [k, current[k]])) as QuickEdit
    const id = current.id

    saving.value = true
    saveError.value = null
    failedField.value = null
    Object.assign(current, changes)
    try {
      const saved = await updateEntry(id, changes)
      // 저장하는 사이 다른 게임으로 옮겼으면 답을 버린다
      if (entry.value?.id === id) entry.value = saved
      return true
    } catch (e) {
      if (entry.value?.id !== id) return false
      // 다른 탭에서 지운 기록 ─ 되돌릴 대상이 없다
      if (e instanceof ApiError && e.status === 404) {
        entry.value = null
        notFound.value = true
        return false
      }
      Object.assign(current, previous)
      saveError.value = message(e)
      failedField.value = keys[0] ?? null
      return false
    } finally {
      saving.value = false
    }
  }

  const changeStatus = (status: EntryStatus) => save({ status })

  /** 같은 별을 다시 누르면 평점을 지운다 ─ 등록 폼과 같은 동작 (S-03) */
  function rate(n: number) {
    const current = entry.value
    if (!current) return Promise.resolve(false)
    return save({ rating: current.rating === n ? null : n })
  }

  /** 앞뒤 공백을 지우고, 비었으면 null로 지운다 ─ 빈 따옴표 "" 가 화면에 남지 않게 */
  function saveReview(text: string) {
    const review = text.trim()
    return save({ review: review || null })
  }

  return { entry, loading, loadError, notFound, saving, saveError, failedField, load, changeStatus, rate, saveReview }
}
