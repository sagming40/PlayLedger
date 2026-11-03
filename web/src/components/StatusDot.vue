<script setup lang="ts">
import type { EntryStatus } from '@/api/entries'
import { STATUS_DOT_CLASS } from '@/lib/entry-display'

// 상태 색 점 ─ 크기는 쓰는 쪽이 class로 정한다 (size-2 등)
// 장식이라 화면 읽기 프로그램에는 숨긴다. 색만으로 구분하지 않게 옆에 글자를 꼭 같이 둔다 (DESIGN 4.1절)
defineProps<{ status: EntryStatus }>()
</script>

<template>
  <span class="shrink-0 rounded-full" :class="STATUS_DOT_CLASS[status]" aria-hidden="true" />
</template>
