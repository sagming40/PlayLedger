<script setup lang="ts">
import { defineAsyncComponent } from 'vue'
import { useRoute } from 'vue-router'
import { ChartColumn, LayoutGrid, Play, Plus, SlidersHorizontal } from '@lucide/vue'
import { Button } from '@/components/ui/button'

// 따로 받는다 ─ Motion이 커서 그대로 묶으면 로그인 화면까지 첫 번들이 gzip 22kB → 68kB가 된다
const AppToast = defineAsyncComponent(() => import('@/components/AppToast.vue'))

// 현재 주소가 어딘지 알려주는 기구. 헤더 제목을 가져와 사용한다
const route = useRoute()

// 메뉴 한 곳에만 적는다
// 메뉴 띠와 하단 탭이 동일한 배열을 돌려 쓰므로, 메뉴를 추가할 때 이 곳만 수정하면 된다
// 두 군데에 나눠 적어놓으면 잊어버리고 한 쪽만 수정하여 데스크톱과 모바일 화면이 제각각이 된다
const menu = [
  { name: 'library', label: '라이브러리', icon: LayoutGrid },
  { name: 'stats', label: '통계', icon: ChartColumn },
  { name: 'settings', label: '설정', icon: SlidersHorizontal },
]

// 등록(/library/new) · 상세(/library/1)도 라이브러리 안의 화면이다 (DESIGN 2.1절)
// RouterLink의 활성 표시는 라우트 부모-자식 관계만 봐서, 형제로 등록된 이 화면들에서는 메뉴가 전부 꺼진다
function isActive(name: string) {
  return route.path.startsWith(`/${name}`)
}
</script>

<template>
  <!-- md: = 48rem 이상. Tailwind의 default가 기준선이다
       rem이라 루트 글꼴 크기에 따라 실제 px이 달라진다 (기본 16px이면 768px)
       색은 전부 style.css 토큰 ─ 다크 · 라이트가 .dark 하나로 같이 바뀐다 (DESIGN 4.4절) -->
  <div class="min-h-screen bg-background text-foreground">
    <!-- 메뉴 띠 ─ hidden(기본 숨김) + md:block(48rem부터 보임) (DESIGN 2.2절)
         sticky: 내려도 맨 위에 붙어 있다. 건물 층별 안내판처럼 어디서든 보이게 -->
    <header class="sticky top-0 z-30 hidden h-18 border-b border-border bg-background md:block">
      <div class="mx-auto flex h-full max-w-7xl items-center gap-6 px-10">
        <RouterLink :to="{ name: 'library' }" aria-label="PlayLedger 홈" class="flex shrink-0 items-center gap-2.5">
          <span class="flex size-8 items-center justify-center rounded-[9px] bg-primary text-primary-foreground" aria-hidden="true">
            <Play class="size-4 fill-current" />
          </span>
          <!-- 띠 안의 부품은 px 크기라 필요한 폭도 px로 정해져 있는데, 48rem은 루트 글꼴이 작은 기기에서 632px까지 내려간다
               그래서 글자는 rem이 아니라 px 기준으로 숨겨 메뉴와 등록 버튼이 겹치지 않게 한다 -->
          <span class="hidden text-base font-extrabold tracking-[0.04em] min-[760px]:inline">PLAYLEDGER</span>
        </RouterLink>
        <nav aria-label="주 메뉴" class="flex shrink-0 gap-1 rounded-full border border-border bg-card p-1">
          <!-- 활성 메뉴만 포인트 색으로 채운다 (DESIGN 4.4절) -->
          <RouterLink
            v-for="item in menu"
            :key="item.name"
            :to="{ name: item.name }"
            class="flex h-9 items-center gap-1.75 rounded-full px-4 text-sm whitespace-nowrap transition-colors"
            :class="
              isActive(item.name)
                ? 'bg-primary font-bold text-primary-foreground'
                : 'font-medium text-muted-foreground hover:text-foreground'
            "
          >
            <component :is="item.icon" class="size-4" aria-hidden="true" />
            {{ item.label }}
          </RouterLink>
        </nav>
        <!-- 등록 화면에서 또 등록 버튼을 보여 줄 이유가 없다 -->
        <Button v-if="route.name !== 'entry-new'" as-child class="ml-auto h-10 shrink-0 px-4 text-sm font-semibold">
          <RouterLink :to="{ name: 'entry-new' }">
            <Plus class="size-4" aria-hidden="true" />
            게임 등록
          </RouterLink>
        </Button>
      </div>
    </header>

    <!-- @container ─ 포스터 벽이 본문 폭 제한을 벗어나 화면 끝까지 깔릴 때 이 상자의 폭을 기준으로 삼는다 (cqw)
         100vw는 스크롤 막대 폭까지 포함해 가로 스크롤이 생긴다. 여백이 있으면 cqw가 그만큼 줄어드니 여백은 안쪽 main에 둔다 -->
    <div class="@container">
      <!-- ownTitle ─ 화면이 제목을 직접 그리는 경우(S-02 포스터 벽 안) 여기서는 그리지 않는다 -->
      <header v-if="!route.meta.ownTitle" class="mx-auto flex max-w-7xl items-center justify-between px-5 pt-5 pb-1 md:px-10 md:pt-8">
        <h1 class="text-2xl font-extrabold tracking-tight md:text-3xl">{{ route.meta.title }}</h1>
        <!-- 오른쪽은 화면별 동작 버튼(+ 등) 자리 -->
      </header>

      <!-- pb-24: 모바일에서 하단 탭이 본문 마지막 줄을 덮지 않게 바닥을 띄운다 -->
      <main class="px-5 py-5 pb-24 md:px-10 md:pb-10">
        <!-- 1200 = 띠의 최대 폭 1280에서 좌우 여백 40씩을 뺀 값. 본문 왼쪽 끝이 로고와 맞는다 -->
        <div class="mx-auto max-w-300">
          <RouterView />
        </div>
      </main>
    </div>

    <!-- 하단 탭 ─ md:hidden(48rem부터 숨김) 화면 아래에 고정 -->
    <nav aria-label="주 메뉴" class="fixed inset-x-0 bottom-0 flex h-16 border-t border-border bg-background md:hidden">
      <RouterLink
        v-for="item in menu"
        :key="item.name"
        :to="{ name: item.name }"
        class="flex flex-1 flex-col items-center justify-center gap-0.5 text-[11px]"
        :class="isActive(item.name) ? 'font-semibold text-brand-text' : 'text-muted-foreground'"
      >
        <component :is="item.icon" class="size-5.5" aria-hidden="true" />
        {{ item.label }}
      </RouterLink>
    </nav>

    <!-- 레이아웃에 둔다 ─ 저장하자마자 화면이 넘어가도 알림은 남는다 -->
    <AppToast />
  </div>
</template>
