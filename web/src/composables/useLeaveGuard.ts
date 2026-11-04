import { onBeforeUnmount, onMounted } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const MESSAGE = '저장하지 않은 내용이 있어요. 나갈까요?'

/**
 * 입력하던 것을 잃지 않게 묻는다 (DESIGN 3.3절) ─ 화면 이동과 탭 닫기 · 새로고침 둘 다
 * 로그인이 끝나 밀려나는 경우는 묻지 않는다 ─ 남아 있어도 저장할 수 없다
 */
export function useLeaveGuard(isDirty: () => boolean) {
  const auth = useAuthStore()

  onBeforeRouteLeave(() => {
    if (!isDirty() || !auth.isAuthenticated) return true
    return window.confirm(MESSAGE)
  })

  function onBeforeUnload(event: BeforeUnloadEvent) {
    if (isDirty()) event.preventDefault()
  }
  onMounted(() => window.addEventListener('beforeunload', onBeforeUnload))
  onBeforeUnmount(() => window.removeEventListener('beforeunload', onBeforeUnload))
}
