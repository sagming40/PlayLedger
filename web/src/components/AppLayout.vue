<script setup lang="ts">
import { useRoute } from 'vue-router'
import { ChartColumn, LayoutGrid, SlidersHorizontal } from '@lucide/vue'

// 현재 주소가 어딘지 알려주는 기구. 헤더 제목을 가져와 사용한다
const route = useRoute()

// 메뉴 한 곳에만 적는다
// 사이드바와 하단 탭이 동일한 배열을 돌려 쓰므로, 메뉴를 추가할 때 이 곳만 수정하면 된다
// 두 군데에 나눠 적어놓으면 잊어버리고 한 쪽만 수정하여 데스크톱과 모바일 화면이 제각각이 된다
const menu = [
  { name: 'library', label: '라이브러리', icon: LayoutGrid },
  { name: 'stats', label: '통계', icon: ChartColumn },
  { name: 'settings', label: '설정', icon: SlidersHorizontal },
]
</script>

<template>
  <!-- md: = 48rem 이상. Tailwind의 default가 기준선이다
       rem이라 루트 글꼴 크기에 따라 실제 px이 달라진다 (기본 16px이면 768px)
       색은 전부 style.css 토큰 ─ 다크 · 라이트가 .dark 하나로 같이 바뀐다 (UI_DESIGN 4.4절) -->
  <div class="min-h-screen bg-background text-foreground md:flex">

    <!-- 사이드바 ─ hidden(기본 숨김) + md:flex(48rem부터 보임) -->
    <aside class="hidden md:flex md:w-60 md:shrink-0 md:flex-col md:gap-7 md:border-r md:border-border md:px-4 md:py-7">
      <div class="flex items-center gap-2.5 px-2.5">
        <!-- 로고 점 ─ 화면에서 포인트 색이 쓰이는 몇 안 되는 자리 -->
        <span class="size-2.5 rounded-[3px] bg-primary" aria-hidden="true" />
        <span class="text-[17px] font-extrabold tracking-[0.04em]">PLAYLEDGER</span>
      </div>
      <nav aria-label="주 메뉴" class="flex flex-col gap-1">
        <!-- 활성 메뉴는 색을 꽉 채우지 않고 옅은 바탕 + 포인트 글자색 (UI_DESIGN 4.4절 원칙) -->
        <RouterLink
          v-for="item in menu"
          :key="item.name"
          :to="{ name: item.name }"
          class="flex h-11 items-center gap-2.5 rounded-lg px-3 text-[15px] text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          active-class="!bg-brand-tint !text-brand-text font-semibold"
        >
          <component :is="item.icon" class="size-[18px]" aria-hidden="true" />
          {{ item.label }}
        </RouterLink>
      </nav>
    </aside>

    <!-- 본문 기둥 -->
    <div class="flex min-h-screen min-w-0 flex-1 flex-col">
      <header class="flex items-center justify-between px-5 pt-5 pb-1 md:px-10 md:pt-8">
        <h1 class="text-2xl font-extrabold tracking-tight md:text-3xl">{{ route.meta.title }}</h1>
        <!-- 오른쪽은 화면별 동작 버튼(+ 등) 자리 -->
      </header>

      <!-- pb-24: 모바일에서 하단 탭이 본문 마지막 줄을 덮지 않게 바닥을 띄운다 -->
      <main class="flex-1 px-5 py-5 pb-24 md:px-10 md:pb-10">
        <RouterView />
      </main>
    </div>

    <!-- 하단 탭 ─ md:hidden(48rem부터 숨김) 화면 아래에 고정 -->
    <nav
      aria-label="주 메뉴"
      class="fixed inset-x-0 bottom-0 flex h-16 border-t border-border bg-background md:hidden"
    >
      <RouterLink
        v-for="item in menu"
        :key="item.name"
        :to="{ name: item.name }"
        class="flex flex-1 flex-col items-center justify-center gap-0.5 text-[11px] text-muted-foreground"
        active-class="!text-brand-text font-semibold"
      >
        <component :is="item.icon" class="size-[22px]" aria-hidden="true" />
        {{ item.label }}
      </RouterLink>
    </nav>
  </div>
</template>
