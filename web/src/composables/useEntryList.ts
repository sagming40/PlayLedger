import { computed, ref } from 'vue'
import { listEntries, type Entry, type EntrySort, type EntryStatus } from '@/api/entries'
import { ApiError } from '@/api/errors'
import { DEFAULT_SORT } from '@/lib/entry-display'

// 목록은 20개씩 불러온다 (DESIGN 3.2절). SERVER의 상한(MAX_LIMIT 100)보다 작아야 한다
export const PAGE_SIZE = 20

/**
 * S-02 라이브러리 목록의 상태와 불러오기 (DESIGN 3.2 · 5 · 6장)
 *
 * 스토어(Pinia)가 아니라 화면이 그때그때 만든다 ─ A로 로그아웃하고 B로 로그인하면
 * 화면이 새로 만들어지면서 목록도 비어서 시작한다. 전역에 두면 A의 목록이 B 화면에 남을 수 있다
 * (PLAN M2 완료 기준 "같은 창에서 A → B 전환 시 A의 목록이 남지 않음")
 */
export function useEntryList() {
  const items = ref<Entry[]>([])
  // 지금 거는 상태 필터. null = 전체 (DESIGN 3.2절). 주소의 ?status=가 원본이고 화면이 setStatus로 넘겨준다
  const status = ref<EntryStatus | null>(null)
  // 장르 필터 · 정렬도 주소가 원본이다. null = 전체
  const genre = ref<number | null>(null)
  const sort = ref<EntrySort>(DEFAULT_SORT)
  // 필터에 맞는 전체 개수. 첫 응답 전에는 모른다(null) ─ 0개와 "아직 모름"을 구분해야 빈 상태가 번쩍이지 않는다
  const total = ref<number | null>(null)
  // 요약 줄 `총 42개 · 미시작 18개`는 필터와 상관없이 라이브러리 전체 기준이다. 못 받아와도 목록은 보여준다
  const libraryTotal = ref<number | null>(null)
  const backlogTotal = ref<number | null>(null)

  const firstLoading = ref(false) // 처음 불러오는 중 ─ 뼈대(skeleton) 표시
  const firstError = ref<string | null>(null) // 처음부터 실패 ─ 목록 대신 오류 + 다시 시도
  const loadingMore = ref(false) // 추가로 불러오는 중 ─ 목록 아래 작은 표시
  const moreError = ref<string | null>(null) // 추가 불러오기 실패 ─ 이미 받은 목록은 그대로 둔다

  const hasMore = computed(() => total.value !== null && items.value.length < total.value)
  // 라이브러리가 통째로 비었다 ─ 등록을 권한다. 필터 결과만 빈 것과 다르다 (DESIGN 5장)
  const isEmpty = computed(() => libraryTotal.value === 0 || (status.value === null && genre.value === null && total.value === 0))
  // 이 상태의 게임만 없다 ─ 안내만 한다 (DESIGN 5장 "필터 결과 없음")
  const isFilterEmpty = computed(() => (status.value !== null || genre.value !== null) && total.value === 0 && !isEmpty.value)

  // 몇 번째 목록인지 ─ 필터를 빠르게 바꾸면 앞 필터의 답(첫 페이지 · 추가 페이지)이 늦게 와서 섞일 수 있다
  // 필터가 바뀔 때마다 번호를 올리고, 답이 왔을 때 번호가 다르면 버린다
  let generation = 0

  function message(e: unknown) {
    return e instanceof ApiError ? e.message : '목록을 불러오지 못했습니다'
  }

  // 같은 기록이 두 페이지에 걸쳐 오면 하나만 남긴다
  // 목록은 최근 수정순이라, 불러오는 사이 다른 탭에서 기록을 고치면 순서가 밀려 겹칠 수 있다
  function append(next: Entry[]) {
    const seen = new Set(items.value.map((e) => e.id))
    items.value = items.value.concat(next.filter((e) => !seen.has(e.id)))
  }

  // 지금 필터 · 정렬을 요청 값으로
  function query() {
    return {
      ...(status.value ? { status: status.value } : {}),
      ...(genre.value !== null ? { genre: genre.value } : {}),
      ...(sort.value !== DEFAULT_SORT ? { sort: sort.value } : {}),
    }
  }

  // 요약 줄 숫자 하나 ─ limit=1로 개수(total)만 쓴다. 실패하면 null(그 숫자만 숨긴다)
  function countOf(filter: EntryStatus | null): Promise<number | null> {
    const params = filter ? { status: filter, limit: 1, offset: 0 } : { limit: 1, offset: 0 }
    return listEntries(params)
      .then((r) => r.total)
      .catch(() => null)
  }

  async function loadFirst() {
    const gen = ++generation
    firstLoading.value = true
    firstError.value = null
    moreError.value = null
    loadingMore.value = false
    try {
      const current = status.value
      const pageRequest = listEntries({ ...query(), limit: PAGE_SIZE, offset: 0 })
      // 목록과 개수를 동시에 묻는다. 목록 응답의 total로 알 수 있는 개수는 다시 묻지 않는다
      // (전체 보기면 전체 개수, 미시작 필터면 미시작 개수가 목록 total과 같다. 장르를 걸면 같지 않다)
      const noGenre = genre.value === null
      const [page, all, backlog] = await Promise.all([
        pageRequest,
        current === null && noGenre ? pageRequest.then((p) => p.total) : countOf(null),
        current === 'BACKLOG' && noGenre ? pageRequest.then((p) => p.total) : countOf('BACKLOG'),
      ])
      if (gen !== generation) return
      items.value = page.items
      total.value = page.total
      libraryTotal.value = all
      backlogTotal.value = backlog
    } catch (e) {
      if (gen !== generation) return
      firstError.value = message(e)
    } finally {
      if (gen === generation) firstLoading.value = false
    }
  }

  /**
   * 필터를 바꾸고 첫 페이지부터 다시 부른다
   * 앞 필터의 목록은 바로 지운다 ─ 새 칩이 눌린 채로 앞 필터의 게임이 보이면 잘못 거른 것처럼 읽힌다
   */
  function setFilters(next: { status: EntryStatus | null; genre: number | null; sort: EntrySort }) {
    const same = status.value === next.status && genre.value === next.genre && sort.value === next.sort
    if (same && total.value !== null) return Promise.resolve()
    status.value = next.status
    genre.value = next.genre
    sort.value = next.sort
    items.value = []
    total.value = null
    return loadFirst()
  }

  function setStatus(next: EntryStatus | null) {
    return setFilters({ status: next, genre: genre.value, sort: sort.value })
  }

  async function loadMore() {
    // 스크롤 감지와 버튼이 거의 동시에 부를 수 있다 ─ 진행 중이면 무시 (같은 페이지를 두 번 받지 않는다)
    if (loadingMore.value || firstLoading.value || !hasMore.value) return
    const gen = generation
    loadingMore.value = true
    moreError.value = null
    try {
      const page = await listEntries({ ...query(), limit: PAGE_SIZE, offset: items.value.length })
      if (gen !== generation) return
      append(page.items)
      total.value = page.total
    } catch (e) {
      if (gen !== generation) return
      moreError.value = message(e)
    } finally {
      if (gen === generation) loadingMore.value = false
    }
  }

  return {
    items,
    status,
    genre,
    sort,
    total,
    libraryTotal,
    backlogTotal,
    firstLoading,
    firstError,
    loadingMore,
    moreError,
    hasMore,
    isEmpty,
    isFilterEmpty,
    loadFirst,
    loadMore,
    setStatus,
    setFilters,
  }
}
