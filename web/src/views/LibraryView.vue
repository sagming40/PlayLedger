<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Gamepad2, Plus } from '@lucide/vue'
import { useEntryList } from '@/composables/useEntryList'
import { STATUS_LABEL, cardMetric } from '@/lib/entry-display'
import EntrySummary from '@/components/EntrySummary.vue'
import GameCover from '@/components/GameCover.vue'
import StatusDot from '@/components/StatusDot.vue'
import { Button } from '@/components/ui/button'

// S-02 라이브러리 (DESIGN 3.2절, 그림은 docs/mockups/Library · LibraryMobile · LibraryEmpty)
const list = useEntryList()

// "오늘"은 화면을 연 시점으로 고정한다 ─ 카드마다 new Date()를 부르면 자정에 걸쳐 그릴 때 날짜가 섞인다
const today = new Date()

// 위쪽 포스터 벽 24칸 (DESIGN 4.4절 원칙 ─ 게임 커버가 화면의 주인공)
// 커버가 없는 게임은 대체 표시(제목 앞 두 글자)로 채운다
// 기록이 24개보다 적으면 돌려 써서 칸을 채운다. 0개면 빈 칸(점선)으로 둔다
const wall = computed(() => {
  const source = list.items.value
  if (source.length === 0) return []
  return Array.from({ length: 24 }, (_, i) => source[i % source.length]!.game)
})

// 첫 로딩 뼈대 8장 ─ 목록 자리를 미리 잡아 데이터가 들어올 때 화면이 덜컥 밀리지 않게 한다
const SKELETON_COUNT = 8

// 목록 끝 표지 ─ 화면에 들어오면 다음 20개를 부른다 (DESIGN 3.2절 "끝에 도달하면 추가 로드")
// 미리 400px 전에 부르게 해서 끝에 닿았을 때는 이미 와 있도록 한다
const sentinel = ref<HTMLElement | null>(null)
let observer: IntersectionObserver | null = null

onMounted(() => {
  list.loadFirst()
  observer = new IntersectionObserver(
    (entries) => {
      if (entries.some((e) => e.isIntersecting)) list.loadMore()
    },
    { rootMargin: '400px' },
  )
  // 표지는 목록이 그려진 뒤에야 생긴다 ─ 생기고 없어질 때마다 붙였다 뗀다
  watch(
    sentinel,
    (el, old) => {
      if (old) observer?.unobserve(old)
      if (el) observer?.observe(el)
    },
    { immediate: true },
  )
})

onBeforeUnmount(() => {
  observer?.disconnect()
})
</script>

<template>
  <div class="flex flex-col gap-5">
    <!-- 모바일 헤더 ─ 48rem 미만은 벽 없이 작게. 자주 여는 화면이라 목록이 한 줄이라도 더 보이게 한다 (DESIGN 3.2절, 목업 LibraryMobile)
         -mr-2: 44px 버튼이 본문 오른쪽 끝보다 살짝 나가 목업의 오른쪽 여백 12px에 맞는다
         -mb-3.5: 목록과의 간격을 목업처럼 좁힌다 (바깥 gap 20 - 14 = 6) -->
    <div class="-mt-5 -mb-3.5 md:hidden">
      <div class="-mr-2 flex h-[60px] items-center justify-between">
        <h1 class="text-[22px] font-extrabold tracking-[-0.02em]">라이브러리</h1>
        <Button as-child size="icon" class="size-11">
          <RouterLink :to="{ name: 'entry-new' }" aria-label="게임 등록">
            <Plus class="size-[22px]" aria-hidden="true" />
          </RouterLink>
        </Button>
      </div>
      <EntrySummary :total="list.total.value" :backlog="list.backlogTotal.value" class="mt-1 text-[13px]" />
    </div>

    <!-- 포스터 벽 + 제목 ─ 48rem부터. 레이아웃의 본문 폭 제한을 거슬러 화면 끝까지 깐다 (wall-bleed) -->
    <section class="wall-bleed relative -mt-5 hidden h-[280px] flex-col justify-end overflow-hidden md:flex">
      <div
        aria-hidden="true"
        class="absolute -top-6 right-0 left-0 grid grid-cols-12 gap-2 px-2"
      >
        <template v-if="wall.length">
          <div
            v-for="(game, i) in wall"
            :key="i"
            class="flex aspect-[2/3] items-end overflow-hidden rounded-md bg-secondary opacity-70 dark:opacity-90"
          >
            <GameCover v-slot="{ initials }" :title="game.title" :cover-url="game.cover_url">
              <span class="p-2 text-[11px] leading-tight font-extrabold text-muted-foreground/60">{{ initials }}</span>
            </GameCover>
          </div>
        </template>
        <template v-else>
          <!-- 0개 ─ 커버가 들어올 자리를 점선으로 보여준다 (목업 LibraryEmpty) -->
          <div v-for="i in 24" :key="i" class="aspect-[2/3] rounded-md border border-dashed border-input" />
        </template>
      </div>
      <!-- 아래로 갈수록 배경색으로 사라진다 -->
      <div aria-hidden="true" class="wall-fade absolute inset-0" />

      <!-- 벽은 끝까지 깔려도 제목은 본문 왼쪽 끝에 맞춘다 -->
      <!-- 등록 버튼은 메뉴 띠에 있다 (DESIGN 2.2절) -->
      <div class="relative mx-auto flex w-full max-w-[1280px] flex-col gap-1.5 px-10 pb-2">
        <h1 class="text-[40px] font-extrabold tracking-tight">라이브러리</h1>
        <EntrySummary :total="list.total.value" :backlog="list.backlogTotal.value" class="text-[15px]" />
      </div>
    </section>

    <!-- 첫 로딩 ─ 뼈대 -->
    <div
      v-if="list.firstLoading.value && !list.items.value.length"
      class="card-grid"
      role="status"
      aria-label="목록을 불러오는 중"
    >
      <!-- 모양을 아래 목록 카드와 같게 ─ 모바일에서도 큰 카드로 그리면 데이터가 올 때 화면이 튄다 -->
      <div
        v-for="i in SKELETON_COUNT"
        :key="i"
        class="flex items-center gap-3.5 border-b border-border py-2.5 md:flex-col md:items-stretch md:gap-0 md:overflow-hidden md:rounded-xl md:border md:bg-card md:py-0"
      >
        <div class="aspect-[460/215] w-28 shrink-0 animate-pulse rounded-lg bg-secondary md:w-auto md:rounded-none" />
        <div class="flex min-w-0 flex-1 flex-col gap-2 md:flex-none md:p-3.5">
          <div class="h-4 w-2/3 animate-pulse rounded bg-secondary" />
          <div class="h-3 w-1/2 animate-pulse rounded bg-secondary" />
        </div>
      </div>
    </div>

    <!-- 처음부터 실패 ─ 목록 대신 안내 + 다시 시도 (DESIGN 6장) -->
    <div v-else-if="list.firstError.value" role="alert" class="flex flex-col items-center gap-3 py-16 text-center">
      <p class="text-[15px]">{{ list.firstError.value }}</p>
      <Button variant="outline" class="h-11" @click="list.loadFirst()">다시 시도</Button>
    </div>

    <!-- 0개 ─ 행동을 유도한다 (DESIGN 5장) -->
    <div v-else-if="list.isEmpty.value" class="flex flex-col items-center gap-3.5 py-16 text-center">
      <Gamepad2 class="size-14 text-muted-foreground" stroke-width="1.5" aria-hidden="true" />
      <h2 class="text-[22px] font-bold">아직 등록된 게임이 없어요</h2>
      <p class="text-[15px] text-muted-foreground">산 게임을 하나 등록하면 방치일수부터 세기 시작해요</p>
      <Button as-child class="mt-2 h-12 px-5.5 text-[15px] font-bold">
        <RouterLink :to="{ name: 'entry-new' }">
          <Plus class="size-[18px]" aria-hidden="true" />
          게임 추가하기
        </RouterLink>
      </Button>
    </div>

    <!-- 목록 -->
    <template v-else>
      <ul class="card-grid">
        <li v-for="entry in list.items.value" :key="entry.id">
          <!-- 모바일은 가로 줄(작은 썸네일 + 글자, 목업 LibraryMobile), 48rem부터 카드(목업 Library) -->
          <RouterLink
            :to="{ name: 'entry-detail', params: { id: entry.id } }"
            class="flex h-full items-center gap-3.5 border-b border-border py-2.5 md:flex-col md:items-stretch md:gap-0 md:overflow-hidden md:rounded-xl md:border md:bg-card md:py-0 md:transition-colors md:hover:border-brand-line"
          >
            <!-- 커버 자리 ─ 비율은 Steam header 이미지(460×215)와 같다 -->
            <div class="flex aspect-[460/215] w-28 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-secondary md:w-auto md:rounded-none">
              <GameCover v-slot="{ initials }" :title="entry.game.title" :cover-url="entry.game.cover_url">
                <span class="text-lg font-extrabold tracking-tight text-muted-foreground/40 md:text-[34px]" aria-hidden="true">
                  {{ initials }}
                </span>
              </GameCover>
            </div>
            <div class="flex min-w-0 flex-col gap-1 md:gap-1.5 md:px-3.5 md:pt-3 md:pb-3.5">
              <span class="truncate text-[15px] font-semibold">{{ entry.game.title }}</span>
              <!-- 상태는 점 + 글자 (DESIGN 4.1절 ─ 색만으로 구분하지 않는다) -->
              <span class="flex items-center gap-1.5 text-[13px] text-muted-foreground">
                <StatusDot :status="entry.status" class="size-[7px]" />
                <span class="text-foreground">{{ STATUS_LABEL[entry.status] }}</span>
                <template v-if="cardMetric(entry, today).text">
                  ·
                  <span :class="cardMetric(entry, today).loud ? 'font-bold text-brand-text' : ''">
                    {{ cardMetric(entry, today).text }}
                  </span>
                </template>
              </span>
              <span v-if="entry.game.genres.length" class="text-xs text-muted-foreground">
                {{ entry.game.genres.map((g) => g.name).join(' · ') }}
              </span>
            </div>
          </RouterLink>
        </li>
      </ul>

      <!-- 목록 끝 ─ 추가 로딩 표시 · 실패 시 다시 시도 · 키보드 사용자를 위한 버튼 -->
      <div class="flex flex-col items-center gap-2 py-4">
        <p v-if="list.loadingMore.value" role="status" class="text-sm text-muted-foreground">불러오는 중…</p>
        <template v-else-if="list.moreError.value">
          <p role="alert" class="text-sm">{{ list.moreError.value }}</p>
          <Button variant="outline" class="h-10" @click="list.loadMore()">다시 시도</Button>
        </template>
        <Button
          v-else-if="list.hasMore.value"
          variant="ghost"
          class="h-10 text-muted-foreground"
          @click="list.loadMore()"
        >
          더 불러오기
        </Button>
        <div v-if="list.hasMore.value" ref="sentinel" aria-hidden="true" class="h-px w-full" />
      </div>
    </template>
  </div>
</template>

<style scoped>
/* 모바일 ─ 한 줄에 하나, 줄 사이 간격 없이 구분선으로 (목업 LibraryMobile) */
.card-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
}

/* 48rem부터 카드 그리드 ─ 칸 폭을 정하지 않고 232px 이상으로 들어가는 만큼 (목업 Library)
   48rem은 Tailwind md:와 같은 기준이다 (DESIGN 2.2절) */
@media (min-width: 48rem) {
  .card-grid {
    grid-template-columns: repeat(auto-fill, minmax(232px, 1fr));
    gap: 22px 20px;
  }
}

/* 본문 폭(50%)의 절반과 화면 폭(50cqw)의 절반 차이만큼 양쪽으로 넓힌다
   cqw는 AppLayout의 @container 상자 기준이라 스크롤 막대 폭이 끼지 않는다 */
.wall-bleed {
  margin-inline: calc(50% - 50cqw);
}

/* 포스터 벽이 아래로 갈수록 배경색으로 사라진다 ─ 다크 · 라이트 모두 배경 토큰을 섞는다 */
.wall-fade {
  background: linear-gradient(
    180deg,
    color-mix(in oklab, var(--background) 35%, transparent) 0%,
    color-mix(in oklab, var(--background) 80%, transparent) 55%,
    var(--background) 100%
  );
}
</style>
