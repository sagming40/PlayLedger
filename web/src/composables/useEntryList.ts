import { computed, ref } from 'vue'
import { listEntries, type Entry } from '@/api/entries'
import { ApiError } from '@/api/errors'

// 목록은 20개씩 불러온다 (UI_DESIGN 3.2절). SERVER의 상한(MAX_LIMIT 100)보다 작아야 한다
export const PAGE_SIZE = 20

/**
 * S-02 라이브러리 목록의 상태와 불러오기 (UI_DESIGN 3.2 · 5 · 6장)
 *
 * 스토어(Pinia)가 아니라 화면이 그때그때 만든다 ─ A로 로그아웃하고 B로 로그인하면
 * 화면이 새로 만들어지면서 목록도 비어서 시작한다. 전역에 두면 A의 목록이 B 화면에 남을 수 있다
 * (MILESTONES M2 완료 기준 "같은 창에서 A → B 전환 시 A의 목록이 남지 않음")
 */
export function useEntryList() {
  const items = ref<Entry[]>([])
  // 전체 개수. 첫 응답 전에는 모른다(null) ─ 0개와 "아직 모름"을 구분해야 빈 상태가 번쩍이지 않는다
  const total = ref<number | null>(null)
  // 요약 줄의 "미시작 N개". 못 받아와도 목록은 보여준다
  const backlogTotal = ref<number | null>(null)

  const firstLoading = ref(false) // 처음 불러오는 중 ─ 뼈대(skeleton) 표시
  const firstError = ref<string | null>(null) // 처음부터 실패 ─ 목록 대신 오류 + 다시 시도
  const loadingMore = ref(false) // 추가로 불러오는 중 ─ 목록 아래 작은 표시
  const moreError = ref<string | null>(null) // 추가 불러오기 실패 ─ 이미 받은 목록은 그대로 둔다

  const hasMore = computed(() => total.value !== null && items.value.length < total.value)
  const isEmpty = computed(() => total.value === 0)

  function message(e: unknown) {
    return e instanceof ApiError ? e.message : '목록을 불러오지 못했습니다'
  }

  // 같은 기록이 두 페이지에 걸쳐 오면 하나만 남긴다
  // 목록은 최근 수정순이라, 불러오는 사이 다른 탭에서 기록을 고치면 순서가 밀려 겹칠 수 있다
  function append(next: Entry[]) {
    const seen = new Set(items.value.map((e) => e.id))
    items.value = items.value.concat(next.filter((e) => !seen.has(e.id)))
  }

  async function loadFirst() {
    firstLoading.value = true
    firstError.value = null
    moreError.value = null
    try {
      // 목록과 미시작 개수를 동시에 묻는다. 미시작 개수는 limit=1로 개수(total)만 쓴다
      const [page, backlog] = await Promise.all([
        listEntries({ limit: PAGE_SIZE, offset: 0 }),
        listEntries({ status: 'BACKLOG', limit: 1, offset: 0 }).catch(() => null),
      ])
      items.value = page.items
      total.value = page.total
      backlogTotal.value = backlog?.total ?? null
    } catch (e) {
      firstError.value = message(e)
    } finally {
      firstLoading.value = false
    }
  }

  async function loadMore() {
    // 스크롤 감지와 버튼이 거의 동시에 부를 수 있다 ─ 진행 중이면 무시 (같은 페이지를 두 번 받지 않는다)
    if (loadingMore.value || firstLoading.value || !hasMore.value) return
    loadingMore.value = true
    moreError.value = null
    try {
      const page = await listEntries({ limit: PAGE_SIZE, offset: items.value.length })
      append(page.items)
      total.value = page.total
    } catch (e) {
      moreError.value = message(e)
    } finally {
      loadingMore.value = false
    }
  }

  return {
    items,
    total,
    backlogTotal,
    firstLoading,
    firstError,
    loadingMore,
    moreError,
    hasMore,
    isEmpty,
    loadFirst,
    loadMore,
  }
}
