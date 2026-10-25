import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { refreshAccessToken, setAccessToken, setAuthFailureHandler } from '@/api/client'
import * as authApi from '@/api/auth'
import type { User } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  // ─── 상태 ───────────────────────────────────────────────
  // 화이트보드에 적히는 건 이 둘뿐이다. TOKEN은 여기 없다 (client.ts 담당)
  const user = ref<User | null>(null)

  // 복원을 시도해봤는가 ─ 아직 해보지 않았다면 아직 로그인 여부를 모르는 상태이다
  // 라우터 가드가 "user가 null"인 것으로 판단 → 로그인 화면으로 튕겨버린다
  // 비유: 출근 도장을 아직 찍지 않은 것과, 찍어보니 결근인 것은 엄연히 다르다
  const isReady = ref(false)

  // ─── 파생값 ─────────────────────────────────────────────
  // 로그인 여부는 TOKEN이 아니라 user로 판단한다
  // access TOKEN은 15분마다 사라지지만 그때도 로그인 상태는 유지된다
  const isAuthenticated = computed(() => user.value !== null)

  // 로그인 상태가 어떻게 끝났는가 ─ App.vue가 로그인 화면으로 보낼 때 구분한다
  // 'logout'  = 사용자가 직접 로그아웃 → 로그인 화면으로만 (돌아갈 주소를 기억하지 않는다)
  // 'expired' = 쓰는 도중 세션이 끝남 → 보던 주소를 기억해서, 다시 로그인하면 그 자리로
  const sessionEnd = ref<'logout' | 'expired' | null>(null)

  // 재발급까지 실패하면 client.ts가 이 함수를 부른다 (API_SPEC 3.2절)
  // TOKEN은 client.ts가 이미 비웠다. 여기서는 화이트보드만 지운다
  // 로그인 화면으로 보내는 일은 App.vue가 user가 비는 순간을 보고 한다
  setAuthFailureHandler(() => {
    if (user.value !== null) sessionEnd.value = 'expired'
    user.value = null
  })

  // 진행 중인 복원. 라우터 가드가 연달아 불러도 한 번만 돈다
  let restoring: Promise<void> | null = null

  // ─── 동작 ───────────────────────────────────────────────

  /**
   * 앱 시작 시 refresh COOKIE로 로그인 상태를 되살린다 (API_SPEC 3.3절, UI_DESIGN 2.3절)
   *
   * access TOKEN은 MEMORY에만 있어서 새로고침하면 사라진다. COOKIE가 살아 있으면 다시 받는다
   * 이때의 401은 오류가 아니라 "로그인하지 않은 상태"다 ─ 문구를 띄우지 않는다
   * 성공 · 실패와 관계없이 끝나면 isReady를 켠다. 켜진 뒤에야 가드가 user를 믿고 판단한다
   */
  function restore(): Promise<void> {
    if (isReady.value) return Promise.resolve()
    if (!restoring) {
      restoring = (async () => {
        try {
          // client.ts의 재발급을 그대로 쓴다 ─ 동시 1회 보장이 여기에도 적용된다 (API_SPEC 3.2절 ③원칙)
          if (await refreshAccessToken()) {
            user.value = await authApi.me()
          }
        } catch {
          // 연결 실패 · /me 실패 ─ 비로그인으로 시작한다
          // TOKEN만 남으면 login()에서 막은 "반쯤 로그인된 상태"가 여기서 생기므로 같이 비운다
          setAccessToken(null)
          user.value = null
        } finally {
          isReady.value = true
          restoring = null
        }
      })()
    }
    return restoring
  }

  async function login(email: string, password: string) {
    // ① TOKEN을 받아 client.ts 서랍에 넣는다
    const res = await authApi.login(email, password)
    setAccessToken(res.access_token)

    // ② 그 TOKEN으로 내가 누구인지 물어본다
    // LOGIN 응답에는 TOKEN만 들어있고 유저 정보는 존재하지 않는다 (API_SPEC 3.1절)
    try {
      user.value = await authApi.me()
    } catch (e) {
      // ②가 실패하면 ①에서 넣은 TOKEN도 되돌린다
      // 그대로 두면 "user는 없는데 TOKEN은 붙어 나가는" 반쯤 로그인된 상태가 남는다
      setAccessToken(null)
      throw e
    }
    // 로그인했다면 로그인 여부는 이미 아는 상태다
    isReady.value = true
    sessionEnd.value = null
  }

  async function register(email: string, password: string, nickname: string) {
    // 가입은 가입만 담당한다. 이어서 LOGIN을 할지말지는 화면이 정한다
    await authApi.register(email, password, nickname)
  }

  async function logout() {
    try {
      await authApi.logout()
    } finally {
      // SERVER 호출 성공/실패 여부와 관계없이 이쪽은 반드시 비운다 (API_SPEC 3.4절)
      // "LOGOUT 실패"라는 상태를 사용자에게 만들어주지 않기 위해서이다
      setAccessToken(null)
      // user보다 먼저 적는다 ─ App.vue는 user가 비는 순간 이 값을 읽는다
      sessionEnd.value = 'logout'
      user.value = null
    }
  }

  return { user, isReady, isAuthenticated, sessionEnd, restore, login, register, logout }
})
