<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { AlertDialog, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogTitle } from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

// S-06 계정 삭제 확인 (DESIGN 3.6절)
// AlertDialog ─ 바깥을 눌러도 닫히지 않는다. 비밀번호를 한 번 더 받아 잠시 자리를 비운 사이 지워지지 않게 한다
const open = defineModel<boolean>('open', { required: true })

const props = defineProps<{
  deleting: boolean
  error: string | null
}>()

const emit = defineEmits<{
  confirm: [password: string]
}>()

const password = ref('')
const canSubmit = computed(() => password.value.length > 0 && !props.deleting)

// 닫으면 입력한 비밀번호를 남기지 않는다
watch(open, (isOpen) => {
  if (!isOpen) password.value = ''
})

// 지우는 중에는 Esc로도 닫지 않는다 ─ 닫혀도 삭제는 진행되어 "취소된 줄" 알게 된다
function onOpenChange(next: boolean) {
  if (!props.deleting) open.value = next
}

function onSubmit() {
  if (canSubmit.value) emit('confirm', password.value)
}
</script>

<template>
  <AlertDialog :open="open" @update:open="onOpenChange">
    <AlertDialogContent
      class="flex w-105 max-w-[calc(100vw-32px)] flex-col gap-3 rounded-2xl bg-popover px-6.5 pt-6.5 pb-5.5 text-popover-foreground"
    >
      <AlertDialogTitle class="text-xl font-extrabold tracking-[-0.01em]">계정을 삭제할까요?</AlertDialogTitle>
      <AlertDialogDescription class="text-[15px] leading-[1.55] text-muted-foreground">
        등록한 게임 기록과 계정 정보가 모두 지워져요. 되돌릴 수 없어요.
      </AlertDialogDescription>
      <form class="flex flex-col gap-3" @submit.prevent="onSubmit">
        <div class="flex flex-col gap-2">
          <Label for="delete-password" class="text-sm font-semibold">비밀번호</Label>
          <Input
            id="delete-password"
            v-model="password"
            type="password"
            autocomplete="current-password"
            maxlength="128"
            class="h-11.5"
            :disabled="deleting"
          />
        </div>
        <p v-if="error" role="alert" class="text-[13px] text-destructive">{{ error }}</p>
        <div class="mt-2.5 flex justify-end gap-2.5">
          <AlertDialogCancel type="button" class="mt-0 h-11 px-4.5 text-[15px]" :disabled="deleting">취소</AlertDialogCancel>
          <!-- AlertDialogAction을 쓰지 않는다 ─ 누르는 순간 닫혀서 실패를 이 자리에서 보여 줄 수 없다 -->
          <Button type="submit" variant="destructive" class="h-11 px-4.5 text-[15px] font-bold" :disabled="!canSubmit">
            {{ deleting ? '삭제 중…' : '계정 삭제' }}
          </Button>
        </div>
      </form>
    </AlertDialogContent>
  </AlertDialog>
</template>
