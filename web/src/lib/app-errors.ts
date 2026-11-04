import { ref } from 'vue'

// 어느 화면에서든 예상 못 한 오류가 나면 App.vue가 맨 위에 띠로 보여 준다 (DESIGN 6장)
// 조용히 빈 화면이 되면 사용자는 무엇이 잘못됐는지 알 수 없다
export const appError = ref<string | null>(null)

const UNEXPECTED = '문제가 생겼어요. 새로고침해 주세요.'
const OFFLINE = '인터넷 연결이 끊겨 화면을 불러오지 못했어요. 연결되면 새로고침해 주세요.'
const RELOAD_KEY = 'pl-chunk-reload'
const RELOAD_GAP_MS = 30_000

/**
 * 화면 조각을 받지 못한 오류인가
 *
 * 새 버전을 배포하면 옛 파일 이름이 사라진다. 열어 둔 탭이 옛 이름으로 다음 화면을 부르면 여기에 걸린다
 * 브라우저마다 문구가 달라서 셋을 본다
 */
export function isChunkLoadError(error: unknown): boolean {
  const message = error instanceof Error ? error.message : String(error)
  return /dynamically imported module|Importing a module script failed|Loading (CSS )?chunk/i.test(message)
}

/**
 * 한 번만 새로고침한다. 했으면 true
 * 정말 서버가 죽어 있으면 새로고침해도 또 실패한다 ─ 무한 반복을 막으려고 시각을 적어 둔다
 */
export function reloadOnce(reload: () => void, now = Date.now()): boolean {
  try {
    const last = Number(sessionStorage.getItem(RELOAD_KEY) ?? 0)
    if (now - last < RELOAD_GAP_MS) return false
    sessionStorage.setItem(RELOAD_KEY, String(now))
  } catch {
    // 저장소를 못 쓰면 횟수를 셀 수 없다 ─ 반복할 위험이 있으니 새로고침하지 않고 안내한다
    return false
  }
  reload()
  return true
}

/** router.onError · app.config.errorHandler가 함께 부른다. target은 가려던 주소 */
export function handleAppError(error: unknown, target?: string) {
  console.error(error)
  // 오프라인이면 새 버전 문제가 아니다 ─ 새로고침하면 지금 화면까지 브라우저 오류 페이지로 바뀐다
  const online = navigator.onLine !== false
  if (online && isChunkLoadError(error) && reloadOnce(() => (target ? window.location.assign(target) : window.location.reload()))) return
  appError.value = online ? UNEXPECTED : OFFLINE
}
