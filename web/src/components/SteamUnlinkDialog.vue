<script setup lang="ts">
import { AlertDialog, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogTitle } from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'

// S-06 Steam 연결 해제 확인 (DESIGN 3.6절) ─ 계정 삭제 대화상자(AccountDeleteDialog)와 같은 틀
// 바깥을 눌러도 닫히지 않고, 푸는 중에는 Esc로도 닫지 않는다. 실패하면 열어 둔 채 이유를 보인다
const open = defineModel<boolean>('open', { required: true })

const props = defineProps<{
  unlinking: boolean
  error: string | null
}>()

const emit = defineEmits<{
  confirm: []
}>()

function onOpenChange(next: boolean) {
  if (!props.unlinking) open.value = next
}
</script>

<template>
  <AlertDialog :open="open" @update:open="onOpenChange">
    <AlertDialogContent
      class="flex w-105 max-w-[calc(100vw-32px)] flex-col gap-3 rounded-2xl bg-popover px-6.5 pt-6.5 pb-5.5 text-popover-foreground"
    >
      <AlertDialogTitle class="text-xl font-extrabold tracking-[-0.01em]">Steam 연결을 해제할까요?</AlertDialogTitle>
      <AlertDialogDescription class="text-[15px] leading-[1.55] text-muted-foreground">
        지금까지 가져온 게임 기록은 그대로 남아요. 다시 연결하기 전까지는 동기화되지 않아요.
      </AlertDialogDescription>
      <p v-if="error" role="alert" class="text-[13px] text-destructive">{{ error }}</p>
      <div class="mt-2.5 flex justify-end gap-2.5">
        <AlertDialogCancel type="button" class="mt-0 h-11 px-4.5 text-[15px]" :disabled="unlinking">취소</AlertDialogCancel>
        <!-- AlertDialogAction을 쓰지 않는다 ─ 누르는 순간 닫혀서 실패를 이 자리에서 보여 줄 수 없다 -->
        <Button
          type="button"
          variant="destructive"
          class="h-11 px-4.5 text-[15px] font-bold"
          :disabled="unlinking"
          @click="emit('confirm')"
        >
          {{ unlinking ? '해제 중…' : '연결 해제' }}
        </Button>
      </div>
    </AlertDialogContent>
  </AlertDialog>
</template>
