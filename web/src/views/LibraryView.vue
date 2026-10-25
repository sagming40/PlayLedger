<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Gamepad2, Plus } from '@lucide/vue'
import { useEntryList } from '@/composables/useEntryList'
import { STATUS_DOT_CLASS, STATUS_LABEL, cardMetric, titleInitials } from '@/lib/entry-display'
import { Button } from '@/components/ui/button'

// S-02 라이브러리 (UI_DESIGN 3.2절, 그림은 docs/mockups/Library · LibraryMobile · LibraryEmpty)
const list = useEntryList()

// "오늘"은 화면을 연 시점으로 고정한다 ─ 카드마다 new Date()를 부르면 자정에 걸쳐 그릴 때 날짜가 섞인다
const today = new Date()

// 위쪽 포스터 벽 24칸 (UI_DESIGN 4.4절 원칙 ─ 게임 커버가 화면의 주인공)
// 커버 이미지는 M2.5 이후라, 지금은 커버 없는 게임의 대체 표시(제목 앞 두 글자)로 채운다
// 기록이 24개보다 적으면 돌려 써서 칸을 채운다. 0개면 빈 칸(점선)으로 둔다
const wall = computed(() => {
  const source = list.items.value
  if (source.length === 0) return []
  return Array.from({ length: 24 }, (_, i) => titleInitials(source[i % source.length]!.game.title))
})

// 첫 로딩 뼈대 8장 ─ 목록 자리를 미리 잡아 데이터가 들어올 때 화면이 덜컥 밀리지 않게 한다
const SKELETON_COUNT = 8

// 목록 끝 표지 ─ 화면에 들어오면 다음 20개를 부른다 (UI_DESIGN 3.2절 "끝에 도달하면 추가 로드")
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
    <!-- 포스터 벽 + 제목 ─ 레이아웃의 본문 여백을 거슬러(-mx) 화면 끝까지 깐다 -->
    <section class="relative -mx-5 -mt-5 flex h-[240px] flex-col justify-end overflow-hidden md:-mx-10 md:h-[280px]">
      <div
        aria-hidden="true"
        class="absolute -top-6 right-0 left-0 grid grid-cols-6 gap-2 px-2 md:grid-cols-12"
      >
        <template v-if="wall.length">
          <div
            v-for="(initials, i) in wall"
            :key="i"
            class="flex aspect-[2/3] items-end rounded-md bg-secondary p-2 opacity-70 dark:opacity-90"
          >
            <span class="text-[11px] leading-tight font-extrabold text-muted-foreground/60">{{ initials }}</span>
          </div>
        </template>
        <template v-else>
          <!-- 0개 ─ 커버가 들어올 자리를 점선으로 보여준다 (목업 LibraryEmpty) -->
          <div v-for="i in 24" :key="i" class="aspect-[2/3] rounded-md border border-dashed border-input" />
        </template>
      </div>
      <!-- 아래로 갈수록 배경색으로 사라진다 -->
      <div aria-hidden="true" class="wall-fade absolute inset-0" />

      <div class="relative flex flex-wrap items-end justify-between gap-3 px-5 pb-2 md:px-10">
        <div class="flex flex-col gap-1.5">
          <h1 class="text-[32px] font-extrabold tracking-tight md:text-[40px]">라이브러리</h1>
          <p v-if="list.total.value" class="text-[15px] text-muted-foreground">
            총 <strong class="text-foreground">{{ list.total.value }}</strong>개
            <template v-if="list.backlogTotal.value !== null">
              · 미시작 <strong class="text-brand-text">{{ list.backlogTotal.value }}</strong>개
            </template>
          </p>
        </div>
        <Button as-child class="h-11 rounded-[10px] px-4.5 text-[15px] font-semibold">
          <RouterLink :to="{ name: 'entry-new' }">
            <Plus class="size-[18px]" aria-hidden="true" />
            게임 등록
          </RouterLink>
        </Button>
      </div>
    </section>

    <!-- 첫 로딩 ─ 뼈대 -->
    <div
      v-if="list.firstLoading.value && !list.items.value.length"
      class="card-grid"
      role="status"
      aria-label="목록을 불러오는 중"
    >
      <div v-for="i in SKELETON_COUNT" :key="i" class="overflow-hidden rounded-xl border border-border bg-card">
        <div class="aspect-[460/215] animate-pulse bg-secondary" />
        <div class="flex flex-col gap-2 p-3.5">
          <div class="h-4 w-2/3 animate-pulse rounded bg-secondary" />
          <div class="h-3 w-1/2 animate-pulse rounded bg-secondary" />
        </div>
      </div>
    </div>

    <!-- 처음부터 실패 ─ 목록 대신 안내 + 다시 시도 (UI_DESIGN 6장) -->
    <div v-else-if="list.firstError.value" role="alert" class="flex flex-col items-center gap-3 py-16 text-center">
      <p class="text-[15px]">{{ list.firstError.value }}</p>
      <Button variant="outline" class="h-11 rounded-[10px]" @click="list.loadFirst()">다시 시도</Button>
    </div>

    <!-- 0개 ─ 행동을 유도한다 (UI_DESIGN 5장) -->
    <div v-else-if="list.isEmpty.value" class="flex flex-col items-center gap-3.5 py-16 text-center">
      <Gamepad2 class="size-14 text-muted-foreground" stroke-width="1.5" aria-hidden="true" />
      <h2 class="text-[22px] font-bold">아직 등록된 게임이 없어요</h2>
      <p class="text-[15px] text-muted-foreground">산 게임을 하나 등록하면 방치일수부터 세기 시작해요</p>
      <Button as-child class="mt-2 h-12 rounded-[10px] px-5.5 text-[15px] font-bold">
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
            <!-- 커버 자리 ─ 비율은 Steam header.jpg(460×215)와 같다. 커버는 M2.5 이후, 지금은 대체 표시 -->
            <div class="flex aspect-[460/215] w-28 shrink-0 items-center justify-center rounded-lg bg-secondary md:w-auto md:rounded-none">
              <span class="text-lg font-extrabold tracking-tight text-muted-foreground/40 md:text-[34px]" aria-hidden="true">
                {{ titleInitials(entry.game.title) }}
              </span>
            </div>
            <div class="flex min-w-0 flex-col gap-1 md:gap-1.5 md:px-3.5 md:pt-3 md:pb-3.5">
              <span class="truncate text-[15px] font-semibold">{{ entry.game.title }}</span>
              <!-- 상태는 점 + 글자 (UI_DESIGN 4.1절 ─ 색만으로 구분하지 않는다) -->
              <span class="flex items-center gap-1.5 text-[13px] text-muted-foreground">
                <span class="size-[7px] shrink-0 rounded-full" :class="STATUS_DOT_CLASS[entry.status]" aria-hidden="true" />
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
          <Button variant="outline" class="h-10 rounded-[10px]" @click="list.loadMore()">다시 시도</Button>
        </template>
        <Button
          v-else-if="list.hasMore.value"
          variant="ghost"
          class="h-10 rounded-[10px] text-muted-foreground"
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
   48rem은 Tailwind md:와 같은 기준이다 (UI_DESIGN 2.2절) */
@media (min-width: 48rem) {
  .card-grid {
    grid-template-columns: repeat(auto-fill, minmax(232px, 1fr));
    gap: 22px 20px;
  }
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
