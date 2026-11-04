<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { init, use, type ECharts } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import type { GenreStat } from '@/api/stats'
import { GENRE_ROW_HEIGHT, genreChartOption, type ChartColors } from '@/lib/genre-chart'

// 장르별 완주율 막대 (DESIGN 3.5절). 필요한 부품만 등록한다 ─ echarts 전체를 묶으면 번들이 몇 배가 된다
use([BarChart, GridComponent, TooltipComponent, CanvasRenderer])

const props = defineProps<{ genres: GenreStat[] }>()

const box = ref<HTMLDivElement | null>(null)
const height = computed(() => `${props.genres.length * GENRE_ROW_HEIGHT}px`)

let chart: ECharts | null = null
let resizeObserver: ResizeObserver | null = null
let themeObserver: MutationObserver | null = null

// 캔버스는 CSS 변수를 모른다 ─ 그릴 때마다 지금 테마의 색을 읽어 넘긴다 (DESIGN 4.4절)
function currentColors(): ChartColors {
  const root = getComputedStyle(document.documentElement)
  const token = (name: string) => root.getPropertyValue(name).trim()
  return {
    bar: token('--primary'),
    track: token('--secondary'),
    label: token('--muted-foreground'),
    value: token('--foreground'),
    tooltipBg: token('--popover'),
    tooltipBorder: token('--border'),
    fontFamily: getComputedStyle(document.body).fontFamily,
  }
}

function draw() {
  const animate = !window.matchMedia('(prefers-reduced-motion: reduce)').matches
  chart?.setOption(genreChartOption(props.genres, currentColors(), animate), { notMerge: true })
}

onMounted(() => {
  chart = init(box.value!)
  draw()
  // 창 크기만 보지 않고 상자를 본다 ─ 줄 수가 바뀌어 높이가 달라져도 다시 맞춘다
  resizeObserver = new ResizeObserver(() => chart?.resize())
  resizeObserver.observe(box.value!)
  // 테마는 <html>의 dark 클래스로 바뀐다. 설정 화면 · OS 어느 쪽에서 바꿔도 여기로 온다
  themeObserver = new MutationObserver(draw)
  themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })
})

watch(() => props.genres, draw)

// 지우지 않으면 화면을 드나들 때마다 캔버스와 감시자가 쌓인다
onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  themeObserver?.disconnect()
  chart?.dispose()
  chart = null
})
</script>

<template>
  <!-- 화면 읽기 프로그램에는 StatsView의 표를 읽힌다 ─ 캔버스는 그림이라 글자가 없다 -->
  <div ref="box" aria-hidden="true" :style="{ height }" />
</template>
