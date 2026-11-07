import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { startSteamLink, syncSteam, unlinkSteam } from '@/api/steam'
import { ApiError } from '@/api/errors'
import { callbackNotice, syncNotice, type SteamNotice } from '@/lib/steam-link'

// S-06 Steam 연동 영역 ─ 연결 · 지금 동기화 · 해제 (DESIGN 3.6절, ARCHITECTURE 5.1 · 5.4절)
// 연결 상태의 원본은 auth 스토어의 user(steam_id 등)다. 여기는 "지금 하는 일"과 그 결과 문구만 든다

const FALLBACK = '요청을 처리하지 못했어요. 잠시 후 다시 시도해 주세요.'

function messageOf(e: unknown): string {
  return e instanceof ApiError ? e.message : FALLBACK
}

export function useSteamLink(navigate: (url: string) => void = (url) => window.location.assign(url)) {
  const auth = useAuthStore()

  // 한 번에 하나만 ─ 동기화 중에 해제를 누르거나 연결을 두 번 누르지 않게 버튼을 같이 끈다
  // 비유: 은행 창구 하나. 앞 일이 끝나야 다음 번호를 부른다
  const busy = ref<'start' | 'sync' | 'unlink' | null>(null)
  const notice = ref<SteamNotice | null>(null)
  // 해제 실패는 대화상자 안에 보인다 ─ 닫히지 않은 채로 이유를 알린다 (DESIGN 3.4절 삭제와 같음)
  const unlinkError = ref<string | null>(null)

  /** Steam에서 돌아온 주소의 steam= 결과를 보인다 */
  function showCallbackResult(value: unknown) {
    const result = callbackNotice(value)
    if (result) notice.value = result
  }

  async function startLink() {
    if (busy.value) return
    busy.value = 'start'
    notice.value = null
    try {
      const { redirect_url } = await startSteamLink()
      // 페이지를 떠난다 ─ busy를 풀지 않는다. 풀면 떠나는 사이 버튼이 다시 눌린다
      navigate(redirect_url)
      return
    } catch (e) {
      notice.value = { kind: 'error', text: messageOf(e) }
      // 409 ─ 다른 탭에서 이미 연결했다. 화면을 서버 상태에 맞춘다 (판단은 상태 코드로만, ARCHITECTURE 3.3절 ④원칙)
      if (e instanceof ApiError && e.status === 409) await auth.reloadUser()
    }
    busy.value = null
  }

  async function syncNow() {
    if (busy.value) return
    busy.value = 'sync'
    notice.value = null
    try {
      const result = await syncSteam()
      auth.patchUser({ steam_synced_at: result.synced_at, steam_persona_name: result.steam_persona_name })
      notice.value = syncNotice(result)
    } catch (e) {
      // 409는 비공개 프로필(서버 문구에 고칠 곳이 있다) 또는 다른 탭에서 해제 ─ 문구는 서버 것을 그대로 쓴다
      notice.value = { kind: 'error', text: messageOf(e) }
      if (e instanceof ApiError && e.status === 409) await auth.reloadUser()
    } finally {
      busy.value = null
    }
  }

  /** 성공하면 true ─ 화면이 대화상자를 닫는다 */
  async function unlink(): Promise<boolean> {
    if (busy.value) return false
    busy.value = 'unlink'
    unlinkError.value = null
    try {
      await unlinkSteam()
      auth.patchUser({ steam_id: null, steam_synced_at: null, steam_persona_name: null })
      notice.value = { kind: 'success', text: 'Steam 연결을 해제했어요. 가져온 기록은 그대로 있어요.' }
      return true
    } catch (e) {
      unlinkError.value = messageOf(e)
      return false
    } finally {
      busy.value = null
    }
  }

  return { busy, notice, unlinkError, showCallbackResult, startLink, syncNow, unlink }
}
