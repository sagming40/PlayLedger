<script setup lang="ts">
import { ref } from 'vue'
import { Eye, EyeOff } from '@lucide/vue'
import { Input } from '@/components/ui/input'

// 비밀번호 칸 + 눈 버튼 (DESIGN 3.1절)
// 눈 버튼은 커튼 ─ 걷으면 적은 글자가 보이고, 다시 치면 가려진다. 값 자체는 그대로다
// id · autocomplete · class 같은 속성은 겉 div가 아니라 안쪽 input에 붙인다
defineOptions({ inheritAttrs: false })

const model = defineModel<string>({ required: true })

defineProps<{
  disabled?: boolean
}>()

const visible = ref(false)
</script>

<template>
  <div class="relative">
    <!-- pr-11 ─ 글자가 눈 버튼 밑으로 들어가지 않게 버튼 폭만큼 비운다 -->
    <Input v-bind="$attrs" v-model="model" :type="visible ? 'text' : 'password'" :disabled="disabled" class="password-input pr-11" />
    <!-- type="button" ─ 기본값 submit이면 누르는 순간 폼이 제출된다
         mousedown.prevent ─ 누를 때 칸의 포커스를 뺏지 않는다. 뺏기면 모바일 키보드가 닫혔다 열린다
         w-11 ─ 손가락으로 누를 폭 44px. 다른 버튼(h-11)과 같은 크기 -->
    <button
      type="button"
      class="absolute inset-y-0 right-0 flex w-11 items-center justify-center rounded-r-lg text-muted-foreground hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50"
      :aria-label="visible ? '비밀번호 숨기기' : '비밀번호 보기'"
      :aria-pressed="visible"
      :disabled="disabled"
      @mousedown.prevent
      @click="visible = !visible"
    >
      <EyeOff v-if="visible" class="size-5" aria-hidden="true" />
      <Eye v-else class="size-5" aria-hidden="true" />
    </button>
  </div>
</template>

<style scoped>
/* Edge는 비밀번호 칸에 자기 눈 버튼을 따로 그린다 ─ 두 개가 겹치지 않게 숨긴다 */
.password-input::-ms-reveal,
.password-input::-ms-clear {
  display: none;
}
</style>
