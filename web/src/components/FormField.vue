<script setup lang="ts">
import { Label } from '@/components/ui/label'

// 입력 칸 한 벌 ─ 라벨 + 칸(slot) + 도움말 · 오류
// 도움말 · 오류의 id는 `{id}-help` · `{id}-error`다. 칸의 aria-describedby에서 이 이름으로 가리킨다
defineProps<{
  id: string
  label: string
  // 라벨 옆 필수 표시 *
  required?: boolean
  // 라벨 옆 단위 (원)
  unit?: string
  help?: string
  error?: string
  // S-01처럼 칸이 촘촘한 폼 ─ 라벨 13px, 간격 6px (목업 Login)
  dense?: boolean
}>()
</script>

<template>
  <div class="flex min-w-0 flex-col" :class="dense ? 'gap-1.5' : 'gap-2'">
    <Label :for="id" class="gap-1 font-semibold" :class="dense ? 'text-[13px]' : 'text-sm'">
      {{ label }}
      <span v-if="required" class="text-brand-text">*</span>
      <span v-if="unit" class="font-normal text-muted-foreground">({{ unit }})</span>
    </Label>
    <slot />
    <span v-if="help" :id="`${id}-help`" class="text-xs text-muted-foreground">{{ help }}</span>
    <span v-if="error" :id="`${id}-error`" class="text-xs text-destructive">{{ error }}</span>
  </div>
</template>
