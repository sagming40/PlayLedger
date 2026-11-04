import { ref } from 'vue'
import { ApiError } from '@/api/errors'
import { getStats, type Stats } from '@/api/stats'
import { localToday } from '@/lib/entry-display'
import { OFFLINE_MESSAGE } from './useEntryDetail'

/**
 * S-05 통계 (DESIGN 3.5절). 화면 진입 시마다 새로 받는다
 *
 * useEntryList처럼 화면이 그때그때 만든다 ─ 다른 계정으로 바꿔 로그인해도 앞 계정의 숫자가 남지 않는다
 */
export function useStats() {
  const stats = ref<Stats | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // 실패 뒤 다시 시도를 연달아 눌러도 마지막 답만 쓴다 (useEntryDetail의 번호표와 같다)
  let seq = 0

  async function load() {
    const mine = ++seq
    loading.value = true
    error.value = null
    try {
      const found = await getStats(localToday())
      if (mine === seq) stats.value = found
    } catch (e) {
      if (mine === seq) error.value = e instanceof ApiError ? e.message : OFFLINE_MESSAGE
    } finally {
      if (mine === seq) loading.value = false
    }
  }

  return { stats, loading, error, load }
}
