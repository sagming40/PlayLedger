// 장르별 완주율 차트의 설정 (DESIGN 3.5절, 그림은 docs/mockups/Stats · StatsMobile)
// 화면과 떼어 둔다 ─ 캔버스는 글자를 읽을 수 없어서 "무엇을 그리라고 시켰는지"를 테스트한다

import type { GenreStat } from '@/api/stats'
import { EMPTY_VALUE, formatPercent, formatPlaytime } from './entry-display'

export interface ChartColors {
  bar: string
  track: string
  label: string
  value: string
  tooltipBg: string
  tooltipBorder: string
  fontFamily: string
}

/** 툴팁 한 줄 ─ 막대에 다 못 담은 숫자 (REQUIREMENTS F-11) */
export function genreDetail(genre: GenreStat): string {
  const average = genre.avg_playtime_minutes === null ? EMPTY_VALUE : formatPlaytime(genre.avg_playtime_minutes)
  return `보유 ${genre.total} · 시작 ${genre.started} · 클리어 ${genre.cleared} · 평균 ${average}`
}

// 한 줄 높이 ─ 줄 수에 맞춰 차트 높이를 정한다. 고정하면 장르가 적을 때 막대 사이가 벌어진다
export const GENRE_ROW_HEIGHT = 36

export function genreChartOption(genres: GenreStat[], colors: ChartColors, animate: boolean) {
  const names = genres.map((g) => g.name)
  return {
    animation: animate,
    textStyle: { fontFamily: colors.fontFamily },
    // 왼쪽 장르 이름 · 오른쪽 % 칸 ─ 목업처럼 막대 양옆에 놓는다
    grid: { left: 76, right: 58, top: 0, bottom: 0 },
    // x축은 0 ~ 100 고정 ─ 데이터에 맞춰 늘면 50%가 꽉 찬 막대로 보인다
    xAxis: { type: 'value', min: 0, max: 100, show: false },
    yAxis: [
      {
        type: 'category',
        data: names,
        // 첫 장르를 맨 위로 ─ ECharts는 기본이 아래에서 위로 쌓는다
        inverse: true,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: colors.label, fontSize: 14, width: 68, overflow: 'truncate' },
      },
      {
        type: 'category',
        data: genres.map((g) => formatPercent(g.completion_rate)),
        inverse: true,
        position: 'right',
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: colors.value, fontSize: 15, fontWeight: 700 },
      },
    ],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'none' },
      backgroundColor: colors.tooltipBg,
      borderColor: colors.tooltipBorder,
      textStyle: { color: colors.value, fontSize: 13 },
      // 터치 화면에서 손가락 아래 잘리지 않게 차트 안에 가둔다
      confine: true,
      formatter: (params: { dataIndex: number }[]) => {
        const genre = genres[params[0]?.dataIndex ?? -1]
        return genre ? `${genre.name}<br/>${genreDetail(genre)}` : ''
      },
    },
    series: [
      {
        type: 'bar',
        // 시작한 게임이 없으면(null) 막대를 그리지 않는다. % 칸에는 '—'가 보인다
        data: genres.map((g) => g.completion_rate),
        barWidth: 12,
        itemStyle: { color: colors.bar, borderRadius: 999 },
        showBackground: true,
        backgroundStyle: { color: colors.track, borderRadius: 999 },
      },
    ],
  }
}
