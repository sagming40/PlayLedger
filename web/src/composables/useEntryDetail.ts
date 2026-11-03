import { ref } from 'vue'
import { getEntry, updateEntry, type Entry, type EntryStatus } from '@/api/entries'
import { ApiError } from '@/api/errors'

// 네트워크가 끊겨 SERVER 답 자체가 없을 때 (DESIGN 6장)
const OFFLINE_MESSAGE = '연결에 실패했습니다'

/**
 * S-04 게임 상세의 기록 하나와 상태 변경 (DESIGN 3.4 · 4.3 · 6장)
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
   * 상태만 바꾼다 ─ 수정 화면을 거치지 않는다 (DESIGN 3.4절)
   *
   * 고른 값을 먼저 화면에 반영하고(점 색 · 평점 칸이 바로 바뀐다), 실패하면 원래 값으로 되돌린다
   * 저장 중에는 다시 바꿀 수 없다 ─ 두 요청이 거꾸로 도착하면 화면과 DB가 다른 상태가 된다 (DESIGN 6장 중복 제출 차단)
   * 평점 · 한줄평은 보내지 않는다. 평점 있는 상태를 벗어나도 지우지 않고 숨기기만 한다 (DESIGN 4.3절)
   */
  async function changeStatus(next: EntryStatus) {
    const current = entry.value
    if (!current || saving.value || current.status === next) return
    const previous = current.status
    const id = current.id

    saving.value = true
    saveError.value = null
    current.status = next
    try {
      const saved = await updateEntry(id, { status: next })
      // 저장하는 사이 다른 게임으로 옮겼으면 답을 버린다
      if (entry.value?.id === id) entry.value = saved
    } catch (e) {
      if (entry.value?.id !== id) return
      // 다른 탭에서 지운 기록 ─ 되돌릴 대상이 없다
      if (e instanceof ApiError && e.status === 404) {
        entry.value = null
        notFound.value = true
        return
      }
      current.status = previous
      saveError.value = message(e)
    } finally {
      saving.value = false
    }
  }

  return { entry, loading, loadError, notFound, saving, saveError, load, changeStatus }
}
