<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { cn } from '@/lib/utils'

// 카드 칸 한 장 ─ S-06 설정 · S-03 평점 칸의 바탕 + 테두리 + 모서리 (목업 Settings · Form)
// 안쪽 배치는 쓰는 쪽이 class로 정한다. cn이 겹치는 값을 뒤쪽 우선으로 정리해 줘서 여백도 바꿀 수 있다
const props = defineProps<{ class?: HTMLAttributes['class'] }>()
</script>

<template>
  <section :class="cn('rounded-[14px] border border-border bg-card px-6 py-5.5', props.class)">
    <slot />
  </section>
</template>
