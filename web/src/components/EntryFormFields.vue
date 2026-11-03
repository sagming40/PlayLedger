<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Star } from '@lucide/vue'
import type { EntryStatus, Genre } from '@/api/entries'
import { listGenres } from '@/api/genres'
import FormField from '@/components/FormField.vue'
import StatusDot from '@/components/StatusDot.vue'
import SurfacePanel from '@/components/SurfacePanel.vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { STATUS_LABEL } from '@/lib/entry-display'
import { STATUSES, canRate, parseHours, parsePrice } from '@/lib/entry-form'

// S-03 등록 · 수정이 같이 쓰는 칸 (DESIGN 3.3절, 그림은 docs/mockups/Form)
// 제목은 둘이 달라서(Steam 검색 / 읽기 전용) 화면이 직접 그린다. 값을 어디로 보낼지도 화면이 정한다
const props = defineProps<{
  // 게임에 이미 붙은 장르 ─ 있으면 고를 수 없다 (DATA_MODEL 2.5절). 등록 화면은 넘기지 않는다
  fixedGenres?: Genre[]
}>()

const status = defineModel<EntryStatus>('status', { required: true })
const genreIds = defineModel<number[]>('genreIds', { required: true })
const purchasedAt = defineModel<string>('purchasedAt', { required: true })
const price = defineModel<string>('price', { required: true })
const hours = defineModel<string>('hours', { required: true })
const rating = defineModel<number | null>('rating', { required: true })
const review = defineModel<string>('review', { required: true })

const genres = ref<Genre[]>([])
const genresFailed = ref(false)

const hasFixedGenres = computed(() => !!props.fixedGenres?.length)
const showRating = computed(() => canRate(status.value))
const priceInvalid = computed(() => parsePrice(price.value) === undefined)
const hoursInvalid = computed(() => parseHours(hours.value) === undefined)

async function loadGenres() {
  genresFailed.value = false
  try {
    genres.value = await listGenres()
  } catch {
    genresFailed.value = true // 장르는 선택 항목이다 ─ 못 불러와도 저장은 막지 않는다
  }
}
// 고를 수 없으면 목록이 필요 없다
onMounted(() => {
  if (!hasFixedGenres.value) loadGenres()
})

function toggleGenre(id: number) {
  genreIds.value = genreIds.value.includes(id) ? genreIds.value.filter((g) => g !== id) : [...genreIds.value, id]
}
</script>

<template>
  <fieldset class="flex flex-col gap-2.5">
    <legend class="mb-2.5 text-sm font-semibold">상태 <span class="text-brand-text">*</span></legend>
    <div class="flex flex-wrap gap-2">
      <button
        v-for="s in STATUSES"
        :key="s"
        type="button"
        :aria-pressed="status === s"
        class="inline-flex h-11 items-center gap-2 rounded-[10px] border px-4 text-[15px]"
        :class="status === s ? 'border-brand-line bg-brand-tint font-semibold' : 'border-border bg-card text-muted-foreground'"
        @click="status = s"
      >
        <StatusDot :status="s" class="size-2" />
        {{ STATUS_LABEL[s] }}
      </button>
    </div>
  </fieldset>

  <!-- 이미 붙은 장르 ─ 버튼처럼 보이면 눌러 보게 되니 글자표로만 보인다 -->
  <div v-if="hasFixedGenres" class="flex flex-col gap-2.5">
    <span class="text-sm font-semibold">장르</span>
    <div class="flex flex-wrap gap-2">
      <span
        v-for="g in fixedGenres"
        :key="g.id"
        class="inline-flex h-8 items-center rounded-md bg-secondary px-3 text-sm text-muted-foreground"
      >
        {{ g.name }}
      </span>
    </div>
    <span class="text-xs text-muted-foreground">장르는 게임에 붙어 있어 여기서 바꿀 수 없어요</span>
  </div>

  <fieldset v-else class="flex flex-col gap-2.5">
    <legend class="mb-2.5 text-sm font-semibold">장르 <span class="font-normal text-muted-foreground">· 여러 개 선택</span></legend>
    <div v-if="genresFailed" class="flex items-center gap-3 text-sm text-muted-foreground">
      장르를 불러오지 못했어요
      <Button type="button" variant="outline" class="h-9" @click="loadGenres">다시 시도</Button>
    </div>
    <div v-else class="flex flex-wrap gap-2">
      <button
        v-for="g in genres"
        :key="g.id"
        type="button"
        :aria-pressed="genreIds.includes(g.id)"
        class="h-10 rounded-full border px-3.5 text-sm"
        :class="
          genreIds.includes(g.id)
            ? 'border-brand-line bg-brand-tint font-semibold text-brand-text'
            : 'border-border bg-card text-muted-foreground'
        "
        @click="toggleGenre(g.id)"
      >
        {{ g.name }}
      </button>
    </div>
    <slot name="genre-hint" />
  </fieldset>

  <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
    <FormField id="purchased-at" label="구매일">
      <Input id="purchased-at" v-model="purchasedAt" type="date" class="h-12 bg-card text-[15px]" />
    </FormField>
    <FormField id="price" label="구매가" unit="원" :error="priceInvalid ? '0 이상의 정수로 적어 주세요' : undefined">
      <Input
        id="price"
        v-model="price"
        type="text"
        inputmode="numeric"
        placeholder="66,000"
        :aria-invalid="priceInvalid"
        :aria-describedby="priceInvalid ? 'price-error' : undefined"
        class="h-12 bg-card text-[15px]"
      />
    </FormField>
    <FormField id="hours" label="플레이타임" unit="시간" :error="hoursInvalid ? '숫자로 적어 주세요 (예: 1.5)' : undefined">
      <Input
        id="hours"
        v-model="hours"
        type="text"
        inputmode="decimal"
        placeholder="0"
        :aria-invalid="hoursInvalid"
        :aria-describedby="hoursInvalid ? 'hours-error' : undefined"
        class="h-12 bg-card text-[15px]"
      />
    </FormField>
  </div>

  <!-- 평점 · 한줄평 ─ 끝난 게임에만 (DESIGN 3.3절) -->
  <SurfacePanel v-if="showRating" class="flex flex-col gap-4 px-[22px] py-5">
    <div class="flex flex-col gap-2">
      <span id="rating-label" class="text-sm font-semibold">평점</span>
      <div role="group" aria-labelledby="rating-label" class="flex gap-0.5">
        <button
          v-for="n in 5"
          :key="n"
          type="button"
          class="flex size-11 items-center justify-center"
          :aria-label="`${n}점`"
          :aria-pressed="rating === n"
          @click="rating = rating === n ? null : n"
        >
          <Star
            class="size-7"
            :class="rating !== null && n <= rating ? 'fill-primary text-primary' : 'text-muted-foreground'"
            stroke-width="1.5"
            aria-hidden="true"
          />
        </button>
      </div>
    </div>
    <FormField id="review" label="한줄평">
      <textarea
        id="review"
        v-model="review"
        rows="2"
        maxlength="200"
        placeholder="예: 엔딩 보고 한참 멍했음"
        class="resize-y rounded-[10px] border border-input bg-background px-3.5 py-3 text-[15px] outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
      />
      <span class="self-end text-xs text-muted-foreground">{{ review.length }} / 200</span>
    </FormField>
  </SurfacePanel>
  <p v-else class="text-[13px] text-muted-foreground">평점 · 한줄평은 클리어 또는 포기했을 때 적을 수 있어요</p>
</template>
