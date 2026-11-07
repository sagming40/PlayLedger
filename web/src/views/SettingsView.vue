<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import type { ThemePreference } from '@/lib/theme'
import SurfacePanel from '@/components/SurfacePanel.vue'
import { Button } from '@/components/ui/button'
import AccountDeleteDialog from '@/components/AccountDeleteDialog.vue'
import { ApiError } from '@/api/errors'
import SteamUnlinkDialog from '@/components/SteamUnlinkDialog.vue'
import { useSteamLink } from '@/composables/useSteamLink'
import { formatSyncedAt, steamProfileUrl } from '@/lib/steam-link'

const auth = useAuthStore()
const theme = useThemeStore()
const route = useRoute()
const router = useRouter()

// Steam 연동 (DESIGN 3.6절) ─ 연결 상태는 auth.user가 원본이다
const steam = useSteamLink()
const steamId = computed(() => auth.user?.steam_id ?? null)
const syncedAtText = computed(() => formatSyncedAt(auth.user?.steam_synced_at ?? null))

// Steam에서 돌아오면 주소에 ?steam=결과 가 붙는다 (ARCHITECTURE 5.4절)
// 보인 뒤 주소에서 지운다 ─ 새로고침 · 뒤로 가기로 같은 문구가 또 뜨지 않게. replace라 기록도 쌓이지 않는다
onMounted(() => {
  if (!('steam' in route.query)) return
  steam.showCallbackResult(route.query.steam)
  const rest = { ...route.query }
  delete rest.steam
  void router.replace({ query: rest })
})

const unlinkOpen = ref(false)

function openUnlink() {
  steam.unlinkError.value = null
  unlinkOpen.value = true
}

async function onUnlink() {
  if (await steam.unlink()) unlinkOpen.value = false
}

// 아바타 자리에 닉네임 첫 글자 ─ 사진 업로드는 범위 밖이다
const initial = computed(() => auth.user?.nickname.charAt(0) ?? '')

// 화면 테마 (F-24, DESIGN 3.6 · 4.4절)
const THEME_OPTIONS: { value: ThemePreference; label: string }[] = [
  { value: 'system', label: '시스템' },
  { value: 'dark', label: '다크' },
  { value: 'light', label: '라이트' },
]

const loggingOut = ref(false)

async function onLogout() {
  loggingOut.value = true
  try {
    // 로그인 화면으로 보내는 일은 App.vue가 한다 ─ user가 비는 순간을 보고 있다
    // 여기서 직접 이동하면 App.vue와 두 번 이동하게 된다
    await auth.logout()
  } finally {
    loggingOut.value = false
  }
}

// 계정 삭제 (DESIGN 3.6절)
const deleteOpen = ref(false)
const deleting = ref(false)
const deleteError = ref<string | null>(null)

function openDelete() {
  deleteError.value = null
  deleteOpen.value = true
}

async function onDelete(password: string) {
  deleting.value = true
  deleteError.value = null
  try {
    // 성공하면 App.vue가 로그인 화면으로 보낸다 ─ 로그아웃과 같다
    await auth.deleteAccount(password)
  } catch (e) {
    deleteError.value = e instanceof ApiError ? e.message : '삭제하지 못했어요. 잠시 후 다시 시도해 주세요.'
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <div class="flex max-w-180 flex-col gap-5">
    <!-- 계정 -->
    <SurfacePanel class="flex items-center gap-4" aria-labelledby="account-title">
      <div
        aria-hidden="true"
        class="flex size-13 shrink-0 items-center justify-center rounded-full border border-brand-line bg-brand-tint text-xl font-extrabold text-brand-text"
      >
        {{ initial }}
      </div>
      <div class="flex min-w-0 flex-col gap-1">
        <h2 id="account-title" class="text-[13px] font-semibold text-muted-foreground">계정</h2>
        <span class="truncate text-lg font-bold">{{ auth.user?.nickname }}</span>
        <span class="truncate text-sm text-muted-foreground">{{ auth.user?.email }}</span>
      </div>
    </SurfacePanel>

    <!-- 화면 테마 ─ 고른 값은 브라우저에 저장되어 로그인 화면에도 적용된다 -->
    <SurfacePanel class="flex flex-wrap items-center justify-between gap-3">
      <h2 id="theme-title" class="text-base font-bold">화면 테마</h2>
      <div role="group" aria-labelledby="theme-title" class="inline-flex gap-1 rounded-xl border border-border bg-background p-1">
        <!-- aria-pressed ─ 화면 읽기 프로그램에 "지금 눌려 있는 버튼"을 알린다 -->
        <button
          v-for="option in THEME_OPTIONS"
          :key="option.value"
          type="button"
          :aria-pressed="theme.preference === option.value"
          class="h-10 rounded-lg border px-4 text-sm transition-colors"
          :class="
            theme.preference === option.value
              ? 'border-brand-line bg-brand-tint font-semibold text-brand-text'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          "
          @click="theme.setPreference(option.value)"
        >
          {{ option.label }}
        </button>
      </div>
    </SurfacePanel>

    <!-- Steam 연동 (DESIGN 3.6절) ─ ID를 적지 않고 Steam 로그인으로 잇는다 (decisions/0015) -->
    <SurfacePanel class="flex flex-col gap-3.5" aria-labelledby="steam-title">
      <h2 id="steam-title" class="text-base font-bold">Steam 연동</h2>

      <template v-if="steamId">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="flex min-w-0 flex-col gap-1">
            <!-- 이름을 못 받았으면(null) 연결됐다는 사실만 ─ 다음 동기화가 다시 받는다 -->
            <span class="truncate text-[15px] font-bold">{{ auth.user?.steam_persona_name ?? 'Steam 계정 연결됨' }}</span>
            <a
              :href="steamProfileUrl(steamId)"
              target="_blank"
              rel="noopener noreferrer"
              class="w-fit text-[13px] font-semibold text-brand-text hover:underline"
              >Steam 프로필 보기</a
            >
          </div>
          <Button class="h-11.5 px-4.5 font-semibold" :disabled="steam.busy.value !== null" @click="steam.syncNow">
            {{ steam.busy.value === 'sync' ? '동기화 중…' : '지금 동기화' }}
          </Button>
        </div>
        <span class="text-[13px] text-muted-foreground">마지막 동기화: {{ syncedAtText }}</span>
      </template>

      <div v-else>
        <Button class="h-11.5 px-4.5 font-semibold" :disabled="steam.busy.value !== null" @click="steam.startLink">
          {{ steam.busy.value === 'start' ? 'Steam으로 이동 중…' : 'Steam 계정 연결' }}
        </Button>
      </div>

      <!-- 결과 · 오류는 버튼 옆 그 자리에 (DESIGN 3.1절 "알림창 사용 안 함") ─ aria-live로 화면 읽기 프로그램에도 알린다 -->
      <div aria-live="polite">
        <div
          v-if="steam.notice.value"
          :role="steam.notice.value.kind === 'error' ? 'alert' : 'status'"
          class="flex flex-col gap-1 rounded-[10px] border px-3.5 py-2.5 text-sm"
          :class="
            steam.notice.value.kind === 'error'
              ? 'border-destructive/40 text-destructive'
              : 'border-brand-line bg-brand-tint text-foreground'
          "
        >
          <span class="font-semibold">{{ steam.notice.value.text }}</span>
          <span v-for="line in steam.notice.value.details" :key="line" class="text-[13px] text-muted-foreground">{{ line }}</span>
        </div>
      </div>

      <span class="text-[13px] text-muted-foreground">Steam 프로필의 게임 세부 정보가 공개여야 동기화됩니다</span>

      <div v-if="steamId" class="border-t border-border pt-3">
        <Button
          variant="ghost"
          class="h-10 px-2 text-sm font-semibold text-muted-foreground hover:text-destructive"
          :disabled="steam.busy.value !== null"
          @click="openUnlink"
          >연결 해제</Button
        >
      </div>
    </SurfacePanel>
    <SteamUnlinkDialog
      v-model:open="unlinkOpen"
      :unlinking="steam.busy.value === 'unlink'"
      :error="steam.unlinkError.value"
      @confirm="onUnlink"
    />

    <!-- Discord 연결 ─ M8 -->
    <SurfacePanel class="flex flex-wrap items-center justify-between gap-3">
      <div class="flex items-center gap-2.5">
        <h2 class="text-base font-bold">Discord 연결</h2>
        <span class="rounded-md bg-secondary px-2 py-0.5 text-[11px] font-bold text-muted-foreground">준비 중</span>
      </div>
      <Button variant="secondary" disabled class="h-11 border-border px-4 font-semibold text-muted-foreground disabled:opacity-100"
        >Discord 계정 연결</Button
      >
    </SurfacePanel>

    <div class="pt-1">
      <Button
        variant="outline"
        class="h-11.5 border-brand-line bg-transparent px-5 font-semibold text-brand-text hover:bg-brand-tint hover:text-brand-text dark:border-brand-line dark:bg-transparent"
        :disabled="loggingOut"
        @click="onLogout"
      >
        {{ loggingOut ? '로그아웃 중…' : '로그아웃' }}
      </Button>
    </div>

    <!-- 눈에 띄지 않게 맨 아래 ─ 자주 쓰지 않고 되돌릴 수 없다 -->
    <div class="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-5">
      <RouterLink to="/privacy" class="inline-flex h-11 items-center text-sm font-semibold text-muted-foreground hover:underline"
        >개인정보 안내</RouterLink
      >
      <Button variant="ghost" class="h-11 px-3 text-sm font-semibold text-destructive hover:text-destructive" @click="openDelete"
        >계정 삭제</Button
      >
    </div>
    <AccountDeleteDialog v-model:open="deleteOpen" :deleting="deleting" :error="deleteError" @confirm="onDelete" />
  </div>
</template>
