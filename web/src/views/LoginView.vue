<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { safeRedirect } from '@/router/guard'
import { ApiError } from '@/api/errors'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

// ─── 화면 상태 ─────────────────────────────────────────
// ref = "값이 바뀌면 화면이 알아서 따라 바뀌는 상자"
// 비유: 전광판에 연결된 숫자판. 숫자판을 바꾸면 전광판이 저절로 바뀐다

// 지금 이 화면이 로그인용인지 가입용인지 (주소는 /login 하나로 유지)
const mode = ref<'login' | 'register'>('login')

const email = ref('')
const password = ref('')
const nickname = ref('')

const errorMessage = ref('')
const submitting = ref(false)   // 서버 응답을 기다리는 중인지

// ─── 계산되는 값 ───────────────────────────────────────
// computed = "재료가 바뀌면 자동으로 다시 계산되는 값"
// 비유: 장바구니 합계. 물건을 넣고 뺄 때마다 내가 더하지 않아도 알아서 바뀐다

const isRegister = computed(() => mode.value === 'register')

// 배경 타일 98장(14열 × 7줄 ─ 1440×900 화면을 아래까지 채운다)의 색 ─ 게임 커버 대신 쓰는 추상 타일 (UI_DESIGN 4.4절)
// 로그인 전에는 내 라이브러리를 알 수 없고, 남의 게임 이미지를 쓰면 저작권 문제가 생긴다
// 색은 테마와 무관하게 어두운 포스터 톤이고, 밝기는 아래 template의 opacity가 테마별로 조절한다
const TILE_HUES = ['#2B2140', '#1D2E45', '#3D2A10', '#33301C', '#1F3A2C', '#1C2A33', '#23382B', '#1E3440', '#3A1E24', '#2E2638', '#262630']
const tiles = Array.from({ length: 98 }, (_, i) => TILE_HUES[(i * 7 + Math.floor(i / 14) * 3) % TILE_HUES.length])

// 버튼을 누를 수 있는 상태인가 (UI_DESIGN 3.1절 ─ 빈 값이면 비활성화, 중복 제출 차단)
const canSubmit = computed(() => {
  if (submitting.value) return false                      // 이미 보내는 중이면 잠금
  if (!email.value || !password.value) return false
  if (isRegister.value && !nickname.value) return false   // 가입일 때만 닉네임도 필수
  return true
})

// ─── 동작 ─────────────────────────────────────────────

function switchMode() {
  mode.value = isRegister.value ? 'login' : 'register'
  // 폼을 바꾸면 이전 화면의 흔적은 지운다
  // 에러 문구가 남아 있으면 "가입 화면인데 로그인 실패 메시지"가 떠있는 상태가 되어버린다
  errorMessage.value = ''
  password.value = ''
  nickname.value = ''
}

async function onSubmit() {
  if (!canSubmit.value) return   // 버튼이 비활성이어도 엔터로 들어올 수 있어서 한 번 더 막는다

  submitting.value = true
  errorMessage.value = ''

  try {
    // 가입이면 가입을 먼저 하고, 이어서 같은 정보로 로그인한다
    // 스토어의 register는 가입만 담당하므로 "그 다음 무얼할지"는 이 화면이 정한다
    if (isRegister.value) {
      await auth.register(email.value, password.value, nickname.value)
    }
    await auth.login(email.value, password.value)

    // 가드가 기억해 둔 원래 주소로 돌아간다 (UI_DESIGN 2.3절 "가려던 주소를 기억하는 이유")
    // replace ─ 뒤로가기로 로그인 화면에 다시 오지 않게 기록을 덮어쓴다
    router.replace(safeRedirect(route.query.redirect))
  } catch (e) {
    // SERVER가 준 detail은 그대로 보여줄 수 있는 한국어 문장이다 (API_SPEC 2.3절)
    // ApiError가 아닌 것(코드 버그 등)까지 사용자에게 날것으로 보이면 안 되므로 갈라둔다
    errorMessage.value =
      e instanceof ApiError ? e.message : '알 수 없는 오류가 발생했습니다'
  } finally {
    // 성공이든 실패든 잠금은 반드시 푼다 ─ 스토어 logout의 finally와 같은 이유
    submitting.value = false
  }
}
</script>

<template>
  <div class="relative flex min-h-screen items-center justify-center overflow-hidden bg-background text-foreground">
    <!-- 포스터 벽 ─ 장식이라 화면 읽기 프로그램에는 숨긴다 -->
    <div
      aria-hidden="true"
      class="absolute -top-10 -right-5 -left-5 grid grid-cols-7 gap-2.5 opacity-35 md:grid-cols-14 dark:opacity-75"
    >
      <div v-for="(hue, i) in tiles" :key="i" class="aspect-[2/3] rounded-md" :style="{ background: hue }" />
    </div>
    <!-- 가운데만 진하게 덮는다 ─ 폼이 타일 위에서도 읽히게 -->
    <div aria-hidden="true" class="login-fade absolute inset-0" />

    <main class="relative flex w-full max-w-[380px] flex-col gap-7 px-5 py-12">
      <div class="flex flex-col gap-2.5">
        <div class="flex items-center gap-2.5">
          <span class="size-3 rounded-[3px] bg-primary" aria-hidden="true" />
          <span class="text-xl font-extrabold tracking-[0.04em]">PLAYLEDGER</span>
        </div>
        <h1 class="text-[34px] leading-tight font-extrabold tracking-tight">
          {{ isRegister ? '가입하기' : '다시 오셨네요' }}
        </h1>
        <p class="text-[15px] text-muted-foreground">사놓고 안 한 게임, 이제 숫자로 관리하자</p>
      </div>

      <!-- @submit.prevent ─ form의 기본 동작(페이지 새로고침)을 막고 내 함수만 부른다
           div가 아닌 form을 사용하는 이유: Enter키 제출과 비밀번호 관리자가 공짜로 따라온다 -->
      <form class="flex flex-col gap-4" @submit.prevent="onSubmit">
        <div class="flex flex-col gap-1.5">
          <Label for="email">이메일</Label>
          <!-- v-model ─ 입력칸과 email 상자를 양쪽으로 묶는다
               사용자가 타이핑하면 상자가 바뀌고, 코드가 상자를 바꾸면 칸이 바뀐다 -->
          <Input
            id="email"
            v-model="email"
            type="email"
            autocomplete="email"
            placeholder="you@example.com"
            class="h-11 rounded-[10px] bg-card/85 text-[15px]"
          />
        </div>

        <!-- v-if ─ 거짓이면 아예 그리지 않는다 (숨기는 개념이 아니라 아예 없는 것) -->
        <div v-if="isRegister" class="flex flex-col gap-1.5">
          <Label for="nickname">닉네임</Label>
          <Input
            id="nickname"
            v-model="nickname"
            type="text"
            autocomplete="nickname"
            aria-describedby="nickname-help"
            class="h-11 rounded-[10px] bg-card/85 text-[15px]"
          />
          <!-- 서버 규칙(2~30자)을 미리 알려 422 왕복을 줄인다 (9/30 Backloggd 레퍼런스) -->
          <span id="nickname-help" class="text-xs text-muted-foreground">2~30자</span>
        </div>

        <div class="flex flex-col gap-1.5">
          <Label for="password">비밀번호</Label>
          <!-- : 이 붙으면 "문자 그대로"가 아니라 "이 식을 계산한 값"이라는 뜻
               브라우저 비밀번호 관리자가 가입/로그인을 구분하도록 값을 바꿔준다 -->
          <Input
            id="password"
            v-model="password"
            type="password"
            :autocomplete="isRegister ? 'new-password' : 'current-password'"
            :aria-describedby="isRegister ? 'password-help' : undefined"
            class="h-11 rounded-[10px] bg-card/85 text-[15px]"
          />
          <span v-if="isRegister" id="password-help" class="text-xs text-muted-foreground">최소 8자</span>
        </div>

        <!-- 알림창이 아니라 폼 안의 빨간 텍스트 (UI_DESIGN 3.1절) -->
        <p v-if="errorMessage" role="alert" class="text-sm text-destructive">{{ errorMessage }}</p>

        <Button type="submit" class="mt-1 h-12 w-full rounded-[10px] text-base font-bold" :disabled="!canSubmit">
          {{ submitting ? '처리 중…' : isRegister ? '가입하기' : '로그인' }}
        </Button>
      </form>

      <p class="text-center text-sm text-muted-foreground">
        {{ isRegister ? '이미 계정이 있으신가요?' : '계정이 없으신가요?' }}
        <button
          type="button"
          class="h-11 px-1 font-semibold text-brand-text hover:underline"
          @click="switchMode"
        >
          {{ isRegister ? '로그인' : '가입' }}
        </button>
      </p>
    </main>
  </div>
</template>

<style scoped>
/* 가운데만 진하게, 가장자리로 갈수록 타일이 보이게 ─ 배경색 토큰을 섞어 다크 · 라이트 모두 맞는다 */
.login-fade {
  background: radial-gradient(
    ellipse 46% 70% at 50% 50%,
    color-mix(in oklab, var(--background) 96%, transparent) 0%,
    color-mix(in oklab, var(--background) 86%, transparent) 55%,
    color-mix(in oklab, var(--background) 45%, transparent) 100%
  );
}
</style>
