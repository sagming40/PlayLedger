<script setup lang="ts">
import { AlertDialog, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogTitle } from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'

// S-04 삭제 확인 (DESIGN 3.4절, 그림은 docs/mockups/DeleteDialog)
// AlertDialog ─ 바깥을 눌러도 닫히지 않고, 처음 포커스가 취소에 간다. 되돌릴 수 없는 일이라 실수로 넘어가지 않게
const open = defineModel<boolean>('open', { required: true })

const props = defineProps<{
  title: string
  deleting: boolean
  error: string | null
}>()

const emit = defineEmits<{
  confirm: []
  // 닫힌 뒤 포커스를 돌려줄 자리는 여는 쪽이 안다
  closed: []
}>()

// 지우는 중에는 Esc로도 닫지 않는다 ─ 닫혀도 삭제는 진행되어 "취소된 줄" 알게 된다
function onOpenChange(next: boolean) {
  if (!props.deleting) open.value = next
}

function onCloseAutoFocus(event: Event) {
  event.preventDefault()
  emit('closed')
}
</script>

<template>
  <AlertDialog :open="open" @update:open="onOpenChange">
    <AlertDialogContent
      class="flex w-105 max-w-[calc(100vw-32px)] flex-col gap-3 rounded-2xl bg-popover px-6.5 pt-6.5 pb-5.5 text-popover-foreground shadow-none sm:max-w-[calc(100vw-32px)]"
      @close-auto-focus="onCloseAutoFocus"
    >
      <AlertDialogTitle class="text-xl font-extrabold tracking-[-0.01em]">이 기록을 삭제할까요?</AlertDialogTitle>
      <AlertDialogDescription class="text-[15px] leading-[1.55] wrap-break-word text-muted-foreground">
        <strong class="text-foreground">{{ title }}</strong
        >의 구매일 · 구매가 · 플레이타임 · 평점이 함께 지워져요. 되돌릴 수 없어요.
      </AlertDialogDescription>
      <p v-if="error" role="alert" class="text-[13px] text-destructive">삭제하지 못했어요. {{ error }}</p>
      <div class="mt-2.5 flex justify-end gap-2.5">
        <AlertDialogCancel class="mt-0 h-11 px-4.5 text-[15px]" :disabled="deleting">취소</AlertDialogCancel>
        <!-- AlertDialogAction을 쓰지 않는다 ─ 누르는 순간 닫혀서 실패를 이 자리에서 보여 줄 수 없다 -->
        <Button type="button" class="h-11 px-4.5 text-[15px] font-bold" :disabled="deleting" @click="emit('confirm')">
          {{ deleting ? '삭제 중…' : '삭제' }}
        </Button>
      </div>
    </AlertDialogContent>
  </AlertDialog>
</template>
