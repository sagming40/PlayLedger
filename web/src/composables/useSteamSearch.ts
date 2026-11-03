import { onScopeDispose, ref } from 'vue'
import { searchSteamApps } from '@/api/steam'
import type { SteamApp } from '@/api/steam'

// 입력이 멈추고 이만큼 지나야 검색한다 (DESIGN 3.3절)
// 비유: 말을 끝까지 듣고 대답하기. 글자마다 물어보면 SERVER도 화면도 바쁘기만 하다
export const SEARCH_DELAY_MS = 250
export const MIN_QUERY = 2
// SERVER의 q 최대 길이 ─ 제목 칸은 200자까지 받으므로 잘라서 보낸다. 안 자르면 422
const MAX_QUERY = 100

/**
 * S-03 제목 자동완성의 상태와 검색 (M2.5)
 * 실패해도 입력과 저장은 막지 않는다 ─ 후보가 없을 뿐 직접 입력은 된다 (DESIGN 3.3절)
 */
export function useSteamSearch() {
  const results = ref<SteamApp[]>([])
  const searching = ref(false)
  const searched = ref(false) // 지금 검색어에 대한 답을 받았는가 ─ "후보 없음"을 "아직 모름"과 구분한다
  const failed = ref(false)

  let timer: ReturnType<typeof setTimeout> | null = null
  // 번호표 ─ 앞서 보낸 검색의 답이 늦게 오면 버린다. 안 버리면 'ho'의 답이 'hollow'의 답을 덮어쓴다
  let ticket = 0

  function clear() {
    if (timer) clearTimeout(timer)
    timer = null
    ticket++
    results.value = []
    searching.value = false
    searched.value = false
    failed.value = false
  }

  function search(text: string) {
    clear()
    const q = text.trim()
    if (q.length < MIN_QUERY) return

    const mine = ticket
    timer = setTimeout(async () => {
      searching.value = true
      try {
        const found = await searchSteamApps(q.slice(0, MAX_QUERY))
        if (mine !== ticket) return
        results.value = found
        searched.value = true
      } catch {
        if (mine !== ticket) return
        failed.value = true
      } finally {
        if (mine === ticket) searching.value = false
      }
    }, SEARCH_DELAY_MS)
  }

  // 화면을 떠난 뒤에 검색이 나가지 않게 한다
  onScopeDispose(clear)

  return { results, searching, searched, failed, search, clear }
}
