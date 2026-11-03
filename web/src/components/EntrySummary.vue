<script setup lang="ts">
// S-02 요약 줄 `총 42개 · 미시작 18개` ─ 글자 크기는 쓰는 쪽이 class로 정한다
// 미시작 개수는 따로 묻는 값이라 늦거나 실패할 수 있다. 그때는 총 개수만 보여 준다
defineProps<{
  total: number | null
  backlog: number | null
}>()
</script>

<template>
  <p v-if="total" class="text-muted-foreground">
    총 <strong class="text-foreground">{{ total }}</strong>개
    <template v-if="backlog !== null">
      · 미시작 <strong class="text-brand-text">{{ backlog }}</strong>개
    </template>
  </p>
</template>
