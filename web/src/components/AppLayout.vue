<script setup lang="ts">
import { useRoute } from 'vue-router'

// 현재 주소가 어딘지 알려주는 기구. 헤더 제목을 가져와 사용한다
const route = useRoute()

// 메뉴 한 곳에만 적는다
// 사이드바와 하단 탭이 동일한 배열을 돌려 쓰므로, 메뉴를 추가할 때 이 곳만 수정하면 된다
// 두 군데에 나눠 적어놓으면 잊어버리고 한 쪽만 수정하여 데스크톱과 모바일 화면이 제각각이 된다
const menu = [
  { name: 'library', label: '라이브러리' },
  { name: 'stats', label: '통계' },
  { name: 'settings', label: '설정' },
]
</script>

<template>
  <!-- md: = 768px 이상. Tailwind의 default가 기준선이다 -->
  <div class="min-h-screen bg-background text-foreground md:flex">

    <!-- 사이드바 ─ hidden(기본 숨김) + md:flex(768px부터 보임) -->
    <aside class="hidden md:flex md:w-56 md:shrink-0 md:flex-col md:border-r md:border-border">
      <div class="px-5 py-4 text-lg font-bold tracking-tight">PLAYLEDGER</div>
      <nav class="flex flex-col gap-1 px-3">
        <RouterLink
          v-for="item in menu"
          :key="item.name"
          :to="{ name: item.name }"
          class="rounded-md px-3 py-2 text-sm text-muted-foreground hover:bg-accent"
          active-class="bg-accent font-medium text-accent-foreground"
        >
          {{ item.label }}
        </RouterLink>
      </nav>
    </aside>

    <!-- 본문 기둥 -->
    <div class="flex min-h-screen flex-1 flex-col">
      <header class="flex h-14 items-center justify-between border-b border-border px-4">
        <h1 class="text-base font-semibold">{{ route.meta.title }}</h1>
        <!-- 오른쪽은 화면별 동작 버튼(+ 등) 자리 -->
      </header>

      <!-- pb-20: 모바일에서 하단 탭이 본문 마지막 줄을 덮지 않게 바닥을 띄운다 -->
      <main class="flex-1 px-4 py-5 pb-20 md:pb-5">
        <RouterView />
      </main>
    </div>

    <!-- 하단 탭 ─ md:hidden(768px부터 숨김) 화면 아래에 고정 -->
    <nav
      class="fixed inset-x-0 bottom-0 flex border-t border-border bg-background md:hidden"
    >
      <RouterLink
        v-for="item in menu"
        :key="item.name"
        :to="{ name: item.name }"
        class="flex-1 py-3 text-center text-xs text-muted-foreground"
        active-class="font-medium text-foreground"
      >
        {{ item.label }}
      </RouterLink>
    </nav>
  </div>
</template>
