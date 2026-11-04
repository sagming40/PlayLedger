<script setup lang="ts">
import { computed, defineAsyncComponent, onMounted, ref } from 'vue'
import type { Stats } from '@/api/stats'
import { useStats } from '@/composables/useStats'
import { formatPercent, formatWon } from '@/lib/entry-display'
import { genreDetail, GENRE_ROW_HEIGHT } from '@/lib/genre-chart'
import GameCover from '@/components/GameCover.vue'
import SurfacePanel from '@/components/SurfacePanel.vue'
import { Button } from '@/components/ui/button'

// 차트는 따로 받는다 ─ echarts가 커서 숫자 카드가 차트를 기다리지 않게 한다
const GenreChart = defineAsyncComponent(() => import('@/components/GenreChart.vue'))

// S-05 통계 (DESIGN 3.5절, 그림은 docs/mockups/Stats · StatsMobile). 계산은 전부 서버가 한다
const { stats, loading, error, load } = useStats()
onMounted(load)

const LIST_PREVIEW = 3

// 강조는 "얼마나 안 하고 있는가"를 말하는 두 비율에만 (목업 Stats)
const cards = computed(() => {
  const s: Stats | null = stats.value
  if (!s) return []
  return [
    { label: '총 보유', value: String(s.total), loud: false },
    { label: '미시작', value: String(s.backlog), loud: false },
    { label: '사장률', value: formatPercent(s.abandoned_rate), loud: true },
    { label: '완주율', value: formatPercent(s.completion_rate), loud: true },
  ]
})

const lists = computed(() => {
  const s = stats.value
  if (!s) return []
  return [
    {
      key: 'idle',
      title: '오래 방치된 게임',
      empty: '방치 중인 게임이 없어요',
      rows: s.longest_idle.map((g) => ({ ...g, value: `${g.idle_days}일` })),
    },
    {
      key: 'cost',
      title: '시간당 비용이 높은 게임',
      empty: '구매가와 플레이타임을 적은 게임이 없어요',
      rows: s.highest_cost.map((g) => ({ ...g, value: `${formatWon(g.cost_per_hour)}원/h` })),
    },
  ]
})

// 더보기를 펼친 목록 ─ 화면을 다시 열면 접힌다
const expanded = ref(new Set<string>())
function toggle(key: string) {
  const next = new Set(expanded.value)
  if (!next.delete(key)) next.add(key)
  expanded.value = next
}
</script>

<template>
  <!-- 처음 불러오는 중 ─ 자리만 잡는다 (DESIGN 6장 뼈대) -->
  <div v-if="loading && !stats" role="status" aria-label="통계를 불러오는 중" class="flex flex-col gap-3.5 md:gap-6">
    <div class="stat-cards">
      <div v-for="i in 4" :key="i" class="h-22 animate-pulse rounded-xl bg-secondary md:h-26 md:rounded-[14px]" />
    </div>
    <div class="h-56 animate-pulse rounded-xl bg-secondary md:rounded-[14px]" />
  </div>

  <!-- 네트워크 · 서버 오류 ─ 안내 + 다시 시도 (DESIGN 6장) -->
  <div v-else-if="error" role="alert" class="flex flex-col items-center gap-3 py-16 text-center">
    <p class="text-[15px]">{{ error }}</p>
    <Button variant="outline" class="h-11" @click="load">다시 시도</Button>
  </div>

  <!-- 0개 (DESIGN 5장) -->
  <p v-else-if="stats && stats.total === 0" class="py-16 text-center text-[15px] text-muted-foreground">
    게임을 등록하면 통계가 표시됩니다
  </p>

  <div v-else-if="stats" class="flex flex-col gap-3.5 md:gap-6">
    <!-- 숫자 카드 4개 -->
    <div class="stat-cards">
      <div
        v-for="card in cards"
        :key="card.label"
        class="flex flex-col gap-0.5 rounded-xl border px-4 py-3.5 md:gap-1 md:rounded-[14px] md:px-5.5 md:py-5"
        :class="card.loud ? 'border-brand-line bg-brand-tint' : 'border-border bg-card'"
      >
        <span class="text-[28px] font-extrabold tracking-[-0.03em] md:text-[38px]" :class="card.loud ? 'text-brand-text' : ''">
          {{ card.value }}
        </span>
        <span class="text-[13px] text-muted-foreground md:text-sm">{{ card.label }}</span>
      </div>
    </div>

    <!-- 목록 2개 ─ 칸 폭을 정하지 않고 340px 이상으로 들어가는 만큼 (목업 Stats) -->
    <div class="grid grid-cols-1 gap-3.5 md:grid-cols-[repeat(auto-fit,minmax(340px,1fr))] md:gap-5">
      <SurfacePanel
        v-for="list in lists"
        :key="list.key"
        :aria-labelledby="`${list.key}-title`"
        class="flex min-w-0 flex-col gap-1 rounded-xl px-4 py-3.5 md:gap-2 md:rounded-[14px] md:px-6 md:py-5.5"
      >
        <h2 :id="`${list.key}-title`" class="mb-1 text-[15px] font-bold md:mb-1.5 md:text-base">{{ list.title }}</h2>
        <p v-if="!list.rows.length" class="py-3 text-sm text-muted-foreground">{{ list.empty }}</p>
        <ol v-else class="flex flex-col">
          <li v-for="(row, i) in expanded.has(list.key) ? list.rows : list.rows.slice(0, LIST_PREVIEW)" :key="row.entry_id">
            <RouterLink
              :to="{ name: 'entry-detail', params: { id: row.entry_id } }"
              class="flex min-h-11 items-center gap-3 py-1.5 hover:opacity-90 md:gap-3.5 md:py-2"
            >
              <span class="hidden w-5 shrink-0 text-sm font-bold text-muted-foreground md:block">{{ i + 1 }}</span>
              <span
                class="flex h-7.5 w-16 shrink-0 items-center justify-center overflow-hidden rounded-[5px] bg-secondary md:h-10 md:w-21.5 md:rounded-md"
              >
                <GameCover v-slot="{ initials }" :title="row.title" :cover-url="row.cover_url">
                  <span class="text-xs font-extrabold text-muted-foreground/50" aria-hidden="true">{{ initials }}</span>
                </GameCover>
              </span>
              <span class="min-w-0 flex-1 truncate text-sm font-semibold md:text-[15px]">{{ row.title }}</span>
              <span class="shrink-0 text-sm font-bold text-brand-text md:text-[15px]">{{ row.value }}</span>
            </RouterLink>
          </li>
        </ol>
        <!-- 기본 3개, 더보기로 확장 (DESIGN 3.5절) -->
        <Button
          v-if="list.rows.length > LIST_PREVIEW"
          type="button"
          variant="ghost"
          class="h-11 self-end px-3 text-[13px] font-medium text-muted-foreground md:h-9"
          :aria-expanded="expanded.has(list.key)"
          @click="toggle(list.key)"
        >
          {{ expanded.has(list.key) ? '접기' : '더보기' }}
        </Button>
      </SurfacePanel>
    </div>

    <!-- 장르별 완주율 -->
    <SurfacePanel
      aria-labelledby="genre-title"
      class="flex flex-col gap-3 rounded-xl px-4 py-3.5 md:gap-4 md:rounded-[14px] md:px-6 md:py-5.5"
    >
      <h2 id="genre-title" class="text-[15px] font-bold md:text-base">장르별 완주율</h2>
      <p v-if="!stats.genres.length" class="py-3 text-sm text-muted-foreground">장르를 고른 게임이 없어요</p>
      <template v-else>
        <!-- 차트 조각이 오기 전에도 자리를 잡아 아래가 밀리지 않게 한다 -->
        <div :style="{ minHeight: `${stats.genres.length * GENRE_ROW_HEIGHT}px` }">
          <GenreChart :genres="stats.genres" />
        </div>
        <p class="text-xs text-muted-foreground">완주율은 시작한 게임 중 클리어한 비율이에요. 막대를 누르면 자세한 숫자가 보여요</p>
        <!-- 캔버스를 대신해 화면 읽기 프로그램이 읽는 표 -->
        <!-- 표는 sr-only의 1px 폭을 무시하고 늘어나 모바일 가로 스크롤을 만든다 ─ 감싸는 칸을 숨긴다 -->
        <div class="sr-only">
          <table>
            <caption>
              장르별 완주율
            </caption>
            <thead>
              <tr>
                <th scope="col">장르</th>
                <th scope="col">완주율</th>
                <th scope="col">자세히</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="genre in stats.genres" :key="genre.genre_id">
                <th scope="row">{{ genre.name }}</th>
                <td>{{ formatPercent(genre.completion_rate) }}</td>
                <td>{{ genreDetail(genre) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </SurfacePanel>
  </div>
</template>

<style scoped>
/* 모바일은 2칸, 48rem부터 들어가는 만큼 (목업 StatsMobile · Stats) */
.stat-cards {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

@media (min-width: 48rem) {
  .stat-cards {
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
  }
}
</style>
