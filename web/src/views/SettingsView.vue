<script setup lang="ts">
import { computed, ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import type { ThemePreference } from '@/lib/theme'
import { Button } from '@/components/ui/button'

const auth = useAuthStore()
const theme = useThemeStore()

// 아바타 자리에 닉네임 첫 글자 ─ 사진 업로드는 범위 밖이다
const initial = computed(() => auth.user?.nickname.charAt(0) ?? '')

// 화면 테마 (F-24, UI_DESIGN 3.6 · 4.4절)
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
</script>

<template>
  <div class="flex max-w-[720px] flex-col gap-5">
    <!-- 계정 -->
    <section class="flex items-center gap-4 rounded-[14px] border border-border bg-card p-6" aria-labelledby="account-title">
      <div
        aria-hidden="true"
        class="flex size-[52px] shrink-0 items-center justify-center rounded-full border border-brand-line bg-brand-tint text-xl font-extrabold text-brand-text"
      >
        {{ initial }}
      </div>
      <div class="flex min-w-0 flex-col gap-1">
        <h2 id="account-title" class="text-[13px] font-semibold text-muted-foreground">계정</h2>
        <span class="truncate text-lg font-bold">{{ auth.user?.nickname }}</span>
        <span class="truncate text-sm text-muted-foreground">{{ auth.user?.email }}</span>
      </div>
    </section>

    <!-- 화면 테마 ─ 고른 값은 브라우저에 저장되어 로그인 화면에도 적용된다 -->
    <section class="flex flex-wrap items-center justify-between gap-3 rounded-[14px] border border-border bg-card p-6">
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
    </section>

    <!-- Steam 연동 ─ M8에서 연결한다. 자리와 안내 문구만 먼저 보여준다 (UI_DESIGN 3.6절) -->
    <section class="flex flex-col gap-3.5 rounded-[14px] border border-border bg-card p-6">
      <div class="flex items-center gap-2.5">
        <h2 class="text-base font-bold">Steam 연동</h2>
        <span class="rounded-md bg-secondary px-2 py-0.5 text-[11px] font-bold text-muted-foreground">M8 예정</span>
      </div>
      <div class="flex flex-col gap-2">
        <label for="steam-id" class="text-sm font-semibold text-muted-foreground">Steam ID</label>
        <div class="flex flex-wrap gap-2.5">
          <input
            id="steam-id"
            type="text"
            disabled
            placeholder="7656119…"
            aria-describedby="steam-help"
            class="h-[46px] min-w-0 flex-[1_1_260px] rounded-[10px] border border-border bg-background px-3.5 text-[15px] opacity-60"
          />
          <Button variant="secondary" disabled class="h-[46px] rounded-[10px] px-4.5">지금 동기화</Button>
        </div>
        <span id="steam-help" class="text-[13px] text-muted-foreground">Steam 프로필의 게임 세부 정보가 공개여야 동기화됩니다</span>
      </div>
    </section>

    <!-- Discord 연결 ─ M11 -->
    <section class="flex flex-wrap items-center justify-between gap-3 rounded-[14px] border border-border bg-card p-6">
      <div class="flex items-center gap-2.5">
        <h2 class="text-base font-bold">Discord 연결</h2>
        <span class="rounded-md bg-secondary px-2 py-0.5 text-[11px] font-bold text-muted-foreground">M11 예정</span>
      </div>
      <Button variant="secondary" disabled class="h-11 rounded-[10px]">Discord 계정 연결</Button>
    </section>

    <div class="pt-1">
      <Button
        variant="outline"
        class="h-[46px] rounded-[10px] border-brand-line bg-transparent px-5 font-semibold text-brand-text hover:bg-brand-tint hover:text-brand-text dark:border-brand-line dark:bg-transparent"
        :disabled="loggingOut"
        @click="onLogout"
      >
        {{ loggingOut ? '로그아웃 중…' : '로그아웃' }}
      </Button>
    </div>
  </div>
</template>
