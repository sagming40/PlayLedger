import type { LocationQueryValue, RouteLocationNormalized, RouteLocationRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const HOME = '/library'

/**
 * 로그인 후 돌아갈 주소로 써도 되는 값인지 걸러낸다
 *
 * /login?redirect=… 의 값은 주소창에서 누구나 바꿀 수 있다
 * "/"로 시작하는 우리 사이트 안의 주소만 따라가고, 나머지는 홈으로 보낸다
 * "//evil.com"은 "/"로 시작하지만 브라우저가 다른 사이트로 읽는다 ─ 따로 막는다
 * 비유: 택시 기사가 "아무 데나"가 아니라 우리 동네 주소만 받아주는 것
 */
export function safeRedirect(value: LocationQueryValue | LocationQueryValue[] | undefined): string {
  const target = Array.isArray(value) ? value[0] : value
  if (typeof target !== 'string') return HOME
  if (!target.startsWith('/') || target.startsWith('//') || target.startsWith('/\\')) return HOME
  // 로그인 화면으로 다시 돌아가는 것은 의미가 없다
  if (target === '/login' || target.startsWith('/login?')) return HOME
  return target
}

/**
 * 화면을 옮길 때마다 실행되는 문지기 (UI_DESIGN 2.3절)
 *
 * ① 아직 로그인 여부를 모르면(isReady가 꺼져 있으면) 복원이 끝날 때까지 기다린다
 *    ─ 기다리지 않고 판단하면 로그인된 사용자도 로그인 화면으로 번쩍 밀려난다
 * ② 로그인하지 않았는데 보호된 화면이면 로그인 화면으로. 가려던 주소는 redirect로 기억한다
 * ③ 이미 로그인했는데 로그인 화면이면 원래 가려던 곳(없으면 홈)으로
 */
export async function authGuard(to: RouteLocationNormalized): Promise<true | RouteLocationRaw> {
  const auth = useAuthStore()

  if (!auth.isReady) await auth.restore()

  const isPublic = to.meta.public === true

  if (!isPublic && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  if (to.name === 'login' && auth.isAuthenticated) {
    return safeRedirect(to.query.redirect)
  }

  return true
}
