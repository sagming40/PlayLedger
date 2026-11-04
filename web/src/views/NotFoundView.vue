<script setup lang="ts">
import { Button } from '@/components/ui/button'
</script>

<template>
  <!-- 없는 주소 ─ 말없이 라이브러리로 보내면 주소를 잘못 쳤는지 알 수 없다 -->
  <main class="flex min-h-screen flex-col items-center justify-center gap-3 px-5 text-center">
    <h1 class="text-[22px] font-bold">페이지를 찾을 수 없어요</h1>
    <p class="text-[15px] text-muted-foreground">주소가 잘못됐거나 사라진 페이지예요</p>
    <Button as-child variant="outline" class="mt-2 h-11">
      <RouterLink to="/">처음으로</RouterLink>
    </Button>
  </main>
</template>
