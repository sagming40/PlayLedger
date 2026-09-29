<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ApiError } from '@/api/errors'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'

const router = useRouter()
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
// 비유: 장바구니 합계. 물건을 널고 뺄 때마다 내가 더하지 않아도 알아서 바뀐다

const isRegister = computed(() => mode.value === 'register')

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
  if (!canSubmit.value) return   // 버튼이 비활성이어고 엔터로 들어올 수 있어서 한 번 더 막는다

  submitting.value = true
  errorMessage.value = ''

  try {
    // 가입이면 가입을 먼저 하고, 이어서 같은 정보로 로그인한다
    // 스토어의 register는 가입만 담당하므로 "그 다음 무얼할지"는 이 화면이 정한다
    if (isRegister.value) {
      await auth.register(email.value, password.value, nickname.value)
    }
    await auth.login(email.value, password.value)

    router.push('/library')
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
  <div class="flex min-h-screen items-center justify-center p-4">
    <Card class="w-full max-w-sm">
      <CardHeader class="text-center">
        <CardTitle class="text-2xl">PLAYLEDGER</CardTitle>
        <CardDescription>사놓고 안 한 게임, 이제 관리하자!</CardDescription>
      </CardHeader>

      <CardContent>
        <!-- @submit.prevent ─ form의 기본 동작(페이지 새로고침)을 막고 내 함수만 부른다
             div가 아닌 form을 사용하는 이유: Enter키 제출과 비밀번호 관리자가 공짜로 따라온다 -->
        <form class="space-y-4" @submit.prevent="onSubmit">
          <div class="space-y-2">
            <Label for="email">이메일</Label>
            <!-- v-model ─ 입력칸과 email 상자를 양쪽으로 묶는다
                 사용자가 타이핑하면 상자가 바뀌고, 코드가 상자를 바꾸면 칸이 바뀐다 -->
            <Input id="email" v-model="email" type="email" autocomplete="email" />
          </div>

          <!-- v-if ─ 거짓이면 아예 그리지 않는다 (숨기는 개념이 아니라 아예 없는 것) -->
          <div v-if="isRegister" class="space-y-2">
            <Label for="nickname">닉네임</Label>
            <Input id="nickname" v-model="nickname" type="text" autocomplete="nickname" />
          </div>

          <div class="space-y-2">
            <Label for="password">비밀번호</Label>
            <!-- : 이 붙으면 "문자 그대로"가 아니라 "이 식을 계산한 값"이라는 뜻
                 브라우저 비밀번호 관리자가 가입/로그인을 구분하도록 값을 바꿔준다 -->
            <Input
              id="password"
              v-model="password"
              type="password"
              :autocomplete="isRegister ? 'new-password' : 'current-password'"
            />
          </div>

          <!-- 알림창이 아니라 폼 안의 빨간 텍스트 (UI_DESIGN 3.1절) -->
          <p v-if="errorMessage" class="text-sm text-destructive">{{ errorMessage }}</p>

          <Button type="submit" class="w-full" :disabled="!canSubmit">
            {{ submitting ? '처리 중…' : isRegister ? '가입하기' : '로그인' }}
          </Button>
        </form>
      </CardContent>

      <CardFooter class="justify-center">
        <button
          type="button"
          class="text-sm text-muted-foreground hover:underline"
          @click="switchMode"
        >
          {{ isRegister ? '이미 계정이 있으신가요? 로그인' : '계정이 없으신가요? 가입' }}
        </button>
      </CardFooter>
    </Card>
  </div>
</template>
