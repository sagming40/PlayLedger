<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ChevronLeft, Star } from '@lucide/vue'
import { createEntry } from '@/api/entries'
import type { EntryStatus, Genre } from '@/api/entries'
import { ApiError } from '@/api/errors'
import { listGenres } from '@/api/genres'
import type { SteamApp } from '@/api/steam'
import FormField from '@/components/FormField.vue'
import StatusDot from '@/components/StatusDot.vue'
import SteamTitleField from '@/components/SteamTitleField.vue'
import SurfacePanel from '@/components/SurfacePanel.vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { STATUS_LABEL } from '@/lib/entry-display'
import { STATUSES, buildCreateBody, canRate, issuesMessage, parseHours, parsePrice } from '@/lib/entry-form'

// S-03 게임 등록 (DESIGN 3.3절, 그림은 docs/mockups/Form)
const router = useRouter()

const title = ref('')
const steamApp = ref<SteamApp | null>(null)
const status = ref<EntryStatus>('BACKLOG')
const genreIds = ref<number[]>([])
const purchasedAt = ref('')
const price = ref('')
const hours = ref('')
const rating = ref<number | null>(null)
const review = ref('')

const genres = ref<Genre[]>([])
const genresFailed = ref(false)

const submitting = ref(false)
const errorMessage = ref('')

const showRating = computed(() => canRate(status.value))
const priceInvalid = computed(() => parsePrice(price.value) === undefined)
const hoursInvalid = computed(() => parseHours(hours.value) === undefined)

const body = computed(() =>
  buildCreateBody({
    title: title.value,
    steamApp: steamApp.value,
    status: status.value,
    genreIds: genreIds.value,
    purchasedAt: purchasedAt.value,
    price: price.value,
    hours: hours.value,
    rating: rating.value,
    review: review.value,
  }),
)
const canSubmit = computed(() => body.value !== null && !submitting.value)

async function loadGenres() {
  genresFailed.value = false
  try {
    genres.value = await listGenres()
  } catch {
    genresFailed.value = true // 장르는 선택 항목이다 ─ 못 불러와도 등록은 막지 않는다
  }
}
onMounted(loadGenres)

function toggleGenre(id: number) {
  genreIds.value = genreIds.value.includes(id) ? genreIds.value.filter((g) => g !== id) : [...genreIds.value, id]
}

async function onSubmit() {
  // 버튼이 비활성이어도 엔터로 들어올 수 있어서 한 번 더 막는다
  if (!canSubmit.value || !body.value) return

  submitting.value = true
  errorMessage.value = ''
  try {
    await createEntry(body.value)
    // replace ─ 뒤로가기로 방금 저장한 폼에 돌아와 중복 등록하지 않게 한다
    await router.replace({ name: 'library' })
  } catch (e) {
    if (e instanceof ApiError) {
      errorMessage.value = issuesMessage(e.issues) ?? e.message
    } else {
      errorMessage.value = '알 수 없는 오류가 발생했습니다'
    }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="flex max-w-[760px] flex-col gap-6">
    <RouterLink
      :to="{ name: 'library' }"
      class="inline-flex h-11 items-center gap-1.5 self-start text-sm text-muted-foreground hover:text-foreground"
    >
      <ChevronLeft class="size-[18px]" aria-hidden="true" />
      라이브러리
    </RouterLink>

    <h1 class="text-[34px] font-extrabold tracking-tight">게임 등록</h1>

    <form class="flex flex-col gap-[26px]" @submit.prevent="onSubmit">
      <FormField id="title" label="제목" required>
        <SteamTitleField v-model:title="title" v-model:steam-app="steamApp" />
      </FormField>

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

      <fieldset class="flex flex-col gap-2.5">
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
        <span v-if="steamApp" class="text-xs text-muted-foreground">
          Steam 장르가 있으면 그것이 먼저 쓰여요. 고른 장르는 Steam에 맞는 장르가 없을 때 쓰여요
        </span>
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

      <p v-if="errorMessage" role="alert" class="text-sm text-destructive">{{ errorMessage }}</p>

      <div class="flex justify-end gap-2.5 border-t border-border pt-2">
        <Button as-child variant="outline" class="mt-2 h-[46px] px-[18px] text-[15px]">
          <RouterLink :to="{ name: 'library' }">취소</RouterLink>
        </Button>
        <Button type="submit" class="mt-2 h-[46px] px-[22px] text-[15px] font-bold" :disabled="!canSubmit">
          {{ submitting ? '저장 중…' : '저장' }}
        </Button>
      </div>
    </form>
  </div>
</template>
