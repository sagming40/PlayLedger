import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { setAccessToken } from '@/api/client'
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

  // ─── 동작 ───────────────────────────────────────────────
  async function login(email: string, password: string) {
    // ① TOKEN을 받아 client.ts 서랍에 넣는다
    const res = await authApi.login(email, password)
    setAccessToken(res.access_token)

    // ② 그 TOKEN으로 내가 누구인지 물어본다
    // LOGIN 응답에는 TOKEN만 들어있고 유저 정보는 존재하지 않는다 (API_SPEC 3.1절)
    user.value = await authApi.me()
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
      user.value = null
    }
  }

  return { user, isReady, isAuthenticated, login, register, logout }
})
