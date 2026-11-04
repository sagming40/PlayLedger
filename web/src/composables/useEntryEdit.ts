import { computed, getCurrentScope, onScopeDispose, ref } from 'vue'
import { updateEntry } from '@/api/entries'
import { ApiError } from '@/api/errors'
import { buildUpdateBody, entryToEditForm, issuesMessage, type EntryEditForm } from '@/lib/entry-form'
import { showToast } from '@/lib/toast'
import { OFFLINE_MESSAGE, useEntryDetail } from './useEntryDetail'

/**
 * S-03 수정 모드 ─ 기존 값을 채워서 열고, 바꾼 칸만 저장한다 (DESIGN 3.3 · 4.3절)
 *
 * 불러오기 · 없는 기록 · 늦게 온 답 처리는 useEntryDetail을 그대로 쓴다 ─ 상세 화면과 규칙이 같다
 */
export function useEntryEdit() {
  const detail = useEntryDetail()

  const form = ref<EntryEditForm | null>(null)
  // 처음 채운 값 ─ 무엇이 바뀌었는지 이것과 비교한다
  let initial: EntryEditForm | null = null

  const submitting = ref(false)
  const errorMessage = ref('')

  // 저장 답을 기다리는 사이 화면을 떠나면 그 답으로 사용자를 끌고 가면 안 된다
  let disposed = false
  if (getCurrentScope()) onScopeDispose(() => (disposed = true))

  async function load(id: number) {
    form.value = null
    initial = null
    errorMessage.value = ''
    await detail.load(id)
    // 기다리는 사이 다른 게임을 불렀으면 그쪽 load가 채운다
    const found = detail.entry.value
    if (found?.id === id) {
      form.value = entryToEditForm(found)
      initial = entryToEditForm(found)
    }
  }

  // 잘못된 입력이면 null, 바뀐 게 없으면 빈 객체
  const body = computed(() => (form.value && initial ? buildUpdateBody(form.value, initial) : null))
  const canSubmit = computed(() => body.value !== null && !submitting.value)

  /**
   * 저장에 성공하면 true ─ 화면이 상세로 돌아간다. 실패하면 입력값을 그대로 두고 이유를 보인다
   * 바뀐 게 없으면 요청하지 않는다 ─ 요청하면 updated_at이 바뀌어 목록(최근 수정순) 맨 위로 올라온다
   */
  async function submit(): Promise<boolean> {
    const id = detail.entry.value?.id
    const changes = body.value
    if (id === undefined || !changes || submitting.value) return false
    if (Object.keys(changes).length === 0) return true

    submitting.value = true
    errorMessage.value = ''
    try {
      await updateEntry(id, changes)
      // 화면을 떠났어도 저장은 됐다 ─ 끌고 가지는 않되 알려는 준다
      showToast('저장했어요')
      return !disposed && detail.entry.value?.id === id
    } catch (e) {
      if (disposed || detail.entry.value?.id !== id) return false
      // 다른 탭에서 지운 기록 ─ 고칠 대상이 없다 (ARCHITECTURE 3.8절)
      if (e instanceof ApiError && e.status === 404) {
        detail.entry.value = null
        form.value = null
        detail.notFound.value = true
        return false
      }
      errorMessage.value = e instanceof ApiError ? (issuesMessage(e.issues) ?? e.message) : OFFLINE_MESSAGE
      return false
    } finally {
      submitting.value = false
    }
  }

  return {
    entry: detail.entry,
    loading: detail.loading,
    loadError: detail.loadError,
    notFound: detail.notFound,
    form,
    submitting,
    errorMessage,
    canSubmit,
    load,
    submit,
  }
}
