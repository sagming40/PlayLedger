<script setup lang="ts">
import { watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { loginRouteAfterSessionEnd } from '@/router/guard'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

// 로그인 상태가 끝나면(직접 로그아웃 · 재발급 실패) 로그인 화면으로 보낸다
// 라우터 가드는 "화면을 옮길 때"만 돌아서, 가만히 있는 화면에서는 아무도 보내주지 않는다
// 비유: 문지기는 문을 지나갈 때만 출입증을 보지만, 출입증이 만료되면 방송으로 안내해 내보낸다
// replace ─ 지금 화면 기록을 로그인 화면으로 덮는다. 뒤로가기는 그 이전 화면으로 가고, 가드가 다시 막는다
watch(
  () => auth.isAuthenticated,
  (loggedIn) => {
    if (!loggedIn && auth.isReady && route.meta.public !== true) {
      router.replace(loginRouteAfterSessionEnd(auth.sessionEnd, route.fullPath))
    }
  },
)
</script>

<template>
  <!-- 복원(refresh)이 끝나기 전 ─ 아직 로그인 여부를 모른다 (UI_DESIGN 2.3절)
       이 자리를 비워두지 않으면 로그인된 사용자에게도 로그인 화면이 번쩍 보인다 -->
  <div
    v-if="!auth.isReady"
    role="status"
    aria-live="polite"
    class="flex min-h-screen items-center justify-center text-sm text-muted-foreground"
  >
    불러오는 중…
  </div>
  <RouterView v-else />
</template>
