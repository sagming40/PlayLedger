<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ChevronLeft, EllipsisVertical, Star } from '@lucide/vue'
import type { EntryStatus } from '@/api/entries'
import { useEntryDetail } from '@/composables/useEntryDetail'
import { EMPTY_VALUE, SOURCE_LABEL, STATUS_LABEL, formatPlaytime, formatWon } from '@/lib/entry-display'
import { canRate } from '@/lib/entry-form'
import EntryDeleteDialog from '@/components/EntryDeleteDialog.vue'
import GameCover from '@/components/GameCover.vue'
import StatusDot from '@/components/StatusDot.vue'
import { Button } from '@/components/ui/button'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { libraryPath } from '@/lib/library-return'

// S-04 게임 상세 (DESIGN 3.4절, 그림은 docs/mockups/Detail · DetailMobile · DeleteDialog)
const route = useRoute()
const router = useRouter()
const detail = useEntryDetail()

// 상세 → 상세로 옮겨 가도(주소의 id만 바뀜) 화면은 다시 만들어지지 않는다 ─ id를 지켜보다 다시 부른다
// 주소 규칙이 숫자만 받으므로(router (\d+)) Number가 NaN이 되지 않는다
watch(
  () => route.params.id,
  (id) => {
    if (typeof id === 'string') detail.load(Number(id))
  },
  { immediate: true },
)

const STATUSES = Object.keys(STATUS_LABEL) as EntryStatus[]

const entry = computed(() => detail.entry.value)
// 평가 칸은 클리어 · 포기일 때만 ─ 다른 상태로 바꿔도 값은 남아 있고 숨기기만 한다 (DESIGN 4.3절)
// 플레이중 → 클리어로 바꾸는 순간 입력란이 나타난다 (PLAN M3 완료 기준)
const ratingVisible = computed(() => !!entry.value && canRate(entry.value.status))

// 한줄평은 누르면 입력칸으로 바뀐다 ─ 별처럼 한 번에 저장할 수 없어서 저장 · 취소를 둔다
const editingReview = ref(false)
const reviewDraft = ref('')
const reviewInput = ref<HTMLTextAreaElement | null>(null)

async function startReview() {
  reviewDraft.value = entry.value?.review ?? ''
  editingReview.value = true
  await nextTick()
  reviewInput.value?.focus()
}

async function submitReview() {
  // 실패하면 입력칸을 열어 둔다 ─ 적은 글이 사라지지 않게
  if (await detail.saveReview(reviewDraft.value)) editingReview.value = false
}

// 다른 게임으로 옮기면 쓰던 한줄평 입력칸을 닫는다 ─ 앞 게임에 쓰던 글이 다음 게임에 저장되면 안 된다
watch(
  () => entry.value?.id,
  () => (editingReview.value = false),
)

const deleteOpen = ref(false)
// 대화상자가 닫히면 포커스를 ⋮로 돌려준다 ─ 메뉴는 이미 닫혀서 대화상자가 돌아갈 자리를 모른다
const moreButton = ref<{ $el: HTMLElement } | null>(null)

function askDelete() {
  detail.deleteError.value = null
  deleteOpen.value = true
}

async function confirmDelete() {
  if (!(await detail.remove())) {
    // 다른 탭에서 먼저 지웠으면 "찾을 수 없어요" 화면이 나오므로 대화상자도 닫는다. 그 밖의 실패는 열어 두고 이유를 보인다
    if (detail.notFound.value) deleteOpen.value = false
    return
  }
  deleteOpen.value = false
  // 목록에서 왔으면 뒤로 간다 ─ ?status= 필터가 그대로 남고, 방문 기록에 지운 기록이 앞에 남지 않는다
  const back = window.history.state?.back
  if (typeof back === 'string' && router.resolve(back).name === 'library') router.back()
  else router.replace(libraryPath())
}
</script>

<template>
  <div class="relative flex flex-col gap-6 md:gap-7">
    <!-- 배경 ─ 그 게임 커버를 페이지 위쪽에 깔고 아래로 갈수록 배경색으로 사라진다 (DESIGN 4.4절)
         레이아웃의 본문 폭 제한을 거슬러 화면 끝까지 깐다 (LibraryView의 wall-bleed와 같은 방법) -->
    <div
      aria-hidden="true"
      class="bleed absolute -top-5 h-62.5 overflow-hidden bg-secondary md:h-130 md:[&_img]:scale-110 md:[&_img]:blur-md"
    >
      <template v-if="entry">
        <!-- Steam 커버는 460px 폭이라 넓은 화면에 늘리면 거칠다 ─ 48rem부터 흐리게 깔고, 또렷한 커버는 본문 카드가 맡는다 -->
        <GameCover v-slot="{ initials }" :title="entry.game.title" :cover-url="entry.game.cover_url">
          <span
            class="flex size-full items-center justify-end pr-6 text-[76px] font-extrabold tracking-[-0.04em] whitespace-nowrap text-foreground/[0.07] md:pr-16 md:text-[140px]"
          >
            {{ initials }}
          </span>
        </GameCover>
      </template>
    </div>
    <!-- 위쪽을 얼마나 덮을지는 테마마다 다르다 ─ 라이트는 밝은 배경이라 더 덮어야 글자가 읽힌다 (목업 Detail) -->
    <div aria-hidden="true" class="bleed backdrop-fade absolute -top-5 h-63 [--fade-top:55%] md:h-130.5 dark:[--fade-top:25%]" />

    <!-- 위쪽 줄 ─ 뒤로 · 수정 · ⋮ (목업 Detail · DetailMobile) -->
    <div class="relative -mt-5 flex h-14 items-center justify-between md:mt-0 md:h-11">
      <RouterLink :to="libraryPath()" class="-ml-2.5 inline-flex h-11 items-center gap-1.5 px-2.5 text-sm text-foreground md:ml-0 md:px-0">
        <ChevronLeft class="size-4.5" aria-hidden="true" />
        라이브러리
      </RouterLink>
      <!-- 모바일은 테두리 없이 글자만, 48rem부터 테두리 버튼 -->
      <div v-if="entry" class="-mr-3 flex md:mr-0 md:gap-2">
        <Button
          as-child
          variant="ghost"
          class="h-11 px-3 text-[15px] font-semibold md:h-10 md:border md:border-border md:bg-card md:px-4 md:text-sm md:font-medium"
        >
          <RouterLink :to="{ name: 'entry-edit', params: { id: entry.id } }">수정</RouterLink>
        </Button>
        <!-- modal 끔 ─ 메뉴가 닫히면서 곧바로 대화상자가 열린다. 둘 다 화면을 잠그면 서로의 잠금 해제가 부딪친다 -->
        <DropdownMenu :modal="false">
          <DropdownMenuTrigger as-child>
            <Button
              ref="moreButton"
              type="button"
              variant="ghost"
              size="icon"
              aria-label="더보기"
              :disabled="detail.saving.value"
              class="size-11 md:size-10 md:border md:border-border md:bg-card"
            >
              <EllipsisVertical class="size-5 md:size-4.5" aria-hidden="true" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" :side-offset="6" class="z-40 min-w-32 rounded-[10px]">
            <DropdownMenuItem variant="destructive" class="h-11 rounded-md px-3 text-[15px]" @select="askDelete">삭제</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>

    <!-- 처음 불러오는 중 ─ 자리만 잡는다 (DESIGN 6장 뼈대) -->
    <div
      v-if="detail.loading.value && !entry"
      role="status"
      aria-label="게임 정보를 불러오는 중"
      class="relative flex flex-col gap-4 pt-24 md:pt-30"
    >
      <div class="h-6 w-28 animate-pulse rounded bg-secondary" />
      <div class="h-10 w-2/3 animate-pulse rounded bg-secondary" />
      <div class="h-11 w-48 animate-pulse rounded-[10px] bg-secondary" />
    </div>

    <!-- 없거나 남의 기록 ─ 둘을 구분하지 않는다 (ARCHITECTURE 3.8절) -->
    <div v-else-if="detail.notFound.value" role="alert" class="relative flex flex-col items-center gap-3 py-24 text-center">
      <h1 class="text-[22px] font-bold">게임을 찾을 수 없어요</h1>
      <p class="text-[15px] text-muted-foreground">지워졌거나 주소가 잘못됐어요</p>
      <Button as-child variant="outline" class="mt-2 h-11">
        <RouterLink :to="{ name: 'library' }">라이브러리로</RouterLink>
      </Button>
    </div>

    <!-- 네트워크 · 서버 오류 ─ 안내 + 다시 시도 (DESIGN 6장) -->
    <div v-else-if="detail.loadError.value" role="alert" class="relative flex flex-col items-center gap-3 py-24 text-center">
      <p class="text-[15px]">{{ detail.loadError.value }}</p>
      <Button variant="outline" class="h-11" @click="detail.load(Number(route.params.id))">다시 시도</Button>
    </div>

    <template v-else-if="entry">
      <!-- 제목 · 장르 · 상태 -->
      <section class="relative flex flex-wrap items-end gap-8 pt-24 md:pt-30">
        <!-- 또렷한 커버 ─ 48rem부터. 모바일은 배경이 커버 역할을 한다 (목업 DetailMobile) -->
        <div class="hidden aspect-460/215 max-w-140 flex-[1_1_420px] items-end overflow-hidden rounded-[14px] bg-secondary md:flex">
          <GameCover v-slot="{ initials }" :title="entry.game.title" :cover-url="entry.game.cover_url">
            <span class="p-5 text-[30px] font-extrabold tracking-[-0.02em] text-muted-foreground/50" aria-hidden="true">
              {{ initials }}
            </span>
          </GameCover>
        </div>

        <div class="flex min-w-0 flex-[1_1_300px] flex-col gap-3 md:gap-4">
          <div v-if="entry.game.genres.length" class="flex flex-wrap gap-1.5 md:gap-2">
            <span
              v-for="genre in entry.game.genres"
              :key="genre.id"
              class="inline-flex h-6 items-center rounded-md bg-secondary px-2.5 text-xs font-semibold text-muted-foreground md:h-6.5"
            >
              {{ genre.name }}
            </span>
          </div>
          <h1 class="text-[30px] leading-[1.15] font-extrabold tracking-[-0.03em] wrap-break-word md:text-[40px] md:leading-[1.1]">
            {{ entry.game.title }}
          </h1>

          <!-- 상태 변경 ─ 수정 화면을 거치지 않고 여기서 바로 (DESIGN 3.4절) -->
          <div class="flex items-center gap-2.5 text-[13px] text-muted-foreground md:gap-3">
            <span id="status-label">상태</span>
            <Select
              :model-value="entry.status"
              :disabled="detail.saving.value"
              @update:model-value="(value) => detail.changeStatus(value as EntryStatus)"
            >
              <SelectTrigger
                aria-labelledby="status-label"
                :aria-busy="detail.saving.value"
                class="flex-1 rounded-[10px] bg-card pl-3.5 text-[15px] font-semibold text-foreground data-[size=default]:h-11.5 md:w-auto md:min-w-40 md:flex-none md:data-[size=default]:h-11 dark:bg-card"
              >
                <span class="flex items-center gap-2.5">
                  <StatusDot :status="entry.status" class="size-2" />
                  <SelectValue />
                </span>
              </SelectTrigger>
              <SelectContent>
                <!-- 한 칸 44px ─ 손가락으로 고르는 목록이다 -->
                <SelectItem v-for="s in STATUSES" :key="s" :value="s" class="h-11 text-[15px]">{{ STATUS_LABEL[s] }}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <p v-if="detail.failedField.value === 'status'" role="alert" class="text-[13px] text-destructive">
            상태를 바꾸지 못했어요. {{ detail.saveError.value }}
          </p>

          <span class="hidden text-[13px] text-muted-foreground md:block">출처 · {{ SOURCE_LABEL[entry.source] }}</span>
        </div>
      </section>

      <div class="relative grid max-w-295 grid-cols-1 gap-3 md:grid-cols-[repeat(auto-fit,minmax(320px,1fr))] md:gap-5">
        <!-- 기록 ─ 모바일은 카드 없이 바로 놓는다 (목업 DetailMobile) -->
        <section class="flex flex-col gap-3 md:gap-4.5 md:rounded-[14px] md:border md:border-border md:bg-card md:p-6">
          <h2 class="hidden text-[15px] font-bold text-muted-foreground md:block">기록</h2>
          <dl class="grid grid-cols-3 gap-2.5 md:gap-4">
            <div>
              <dt class="text-xs text-muted-foreground">구매일</dt>
              <!-- 날짜 문자열을 그대로 쓴다 ─ Date로 읽으면 한국 시간으로 하루 전날이 될 수 있다 (CLAUDE.md 함정 "날짜와 시각") -->
              <dd class="mt-0.75 text-[15px] font-bold md:mt-1 md:text-lg">{{ entry.purchased_at ?? EMPTY_VALUE }}</dd>
            </div>
            <div>
              <dt class="text-xs text-muted-foreground">구매가</dt>
              <dd class="mt-0.75 text-[15px] font-bold md:mt-1 md:text-lg">
                {{ entry.purchase_price === null ? EMPTY_VALUE : `${formatWon(entry.purchase_price)}원` }}
              </dd>
            </div>
            <div>
              <dt class="text-xs text-muted-foreground">플레이타임</dt>
              <dd class="mt-0.75 text-[15px] font-bold md:mt-1 md:text-lg">{{ formatPlaytime(entry.playtime_minutes) }}</dd>
            </div>
          </dl>

          <!-- 시간당 비용 ─ 서버 계산값. 강조는 포인트 테두리 + 옅은 바탕 (DESIGN 4.4절) -->
          <div
            class="flex items-baseline justify-between gap-3 rounded-xl border border-brand-line bg-brand-tint px-4 py-3.5 md:px-5 md:py-4.5"
          >
            <span class="text-[13px] text-muted-foreground md:text-sm">시간당 비용</span>
            <span v-if="entry.cost_per_hour !== null" class="text-2xl font-extrabold tracking-[-0.02em] text-brand-text md:text-[30px]">
              {{ formatWon(entry.cost_per_hour) }}<span class="ml-0.75 text-[13px] font-semibold md:ml-1 md:text-[15px]">원/h</span>
            </span>
            <!-- 플레이타임 0 · 구매가 없음 ─ 계산하지 않는다 (DESIGN 3.4절, REQUIREMENTS 5.1절) -->
            <span v-else class="text-2xl font-extrabold text-muted-foreground md:text-[30px]">{{ EMPTY_VALUE }}</span>
          </div>
        </section>

        <!-- 평가 ─ 클리어 · 포기일 때만 (ratingVisible). 여기서 바로 고친다 (DESIGN 3.4 · 4.3절) -->
        <section
          v-if="ratingVisible"
          aria-labelledby="rating-heading"
          class="flex flex-col gap-2.5 rounded-xl border border-border bg-card px-4 py-3.5 md:gap-4.5 md:rounded-[14px] md:p-6"
        >
          <h2 id="rating-heading" class="sr-only text-[15px] font-bold text-muted-foreground md:not-sr-only">평가</h2>

          <!-- 별 ─ 누르면 바로 저장, 같은 별을 다시 누르면 지운다 (S-03 등록 폼과 같은 동작)
               한 칸 44px ─ 손가락으로 누를 수 있는 크기. -ml로 첫 별의 왼쪽 끝을 글자와 맞춘다 -->
          <div class="flex flex-col gap-1">
            <div role="group" aria-label="평점" class="-ml-2.5 flex">
              <button
                v-for="n in 5"
                :key="n"
                type="button"
                class="flex size-11 items-center justify-center disabled:opacity-60"
                :aria-label="`${n}점`"
                :aria-pressed="entry.rating === n"
                :disabled="detail.saving.value"
                @click="detail.rate(n)"
              >
                <Star
                  class="size-5.5 md:size-6.5"
                  :class="entry.rating !== null && n <= entry.rating ? 'fill-brand-text text-brand-text' : 'text-muted-foreground'"
                  stroke-width="1.5"
                  aria-hidden="true"
                />
              </button>
            </div>
            <p v-if="entry.rating === null" class="text-[13px] text-muted-foreground">별을 눌러 평점을 남겨요</p>
            <p v-if="detail.failedField.value === 'rating'" role="alert" class="text-[13px] text-destructive">
              평점을 저장하지 못했어요. {{ detail.saveError.value }}
            </p>
          </div>

          <!-- 한줄평 -->
          <form v-if="editingReview" class="flex flex-col gap-2" @submit.prevent="submitReview">
            <label for="review" class="sr-only">한줄평</label>
            <textarea
              id="review"
              ref="reviewInput"
              v-model="reviewDraft"
              rows="2"
              maxlength="200"
              placeholder="예: 엔딩 보고 한참 멍했음"
              class="resize-y rounded-[10px] border border-input bg-background px-3.5 py-3 text-[15px] outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
              @keydown.esc="editingReview = false"
            />
            <p v-if="detail.failedField.value === 'review'" role="alert" class="text-[13px] text-destructive">
              한줄평을 저장하지 못했어요. {{ detail.saveError.value }}
            </p>
            <div class="flex items-center justify-between gap-2">
              <span class="text-xs text-muted-foreground">{{ reviewDraft.length }} / 200</span>
              <div class="flex gap-2">
                <Button type="button" variant="outline" class="h-10" @click="editingReview = false">취소</Button>
                <Button type="submit" class="h-10 font-semibold" :disabled="detail.saving.value">
                  {{ detail.saving.value ? '저장 중…' : '저장' }}
                </Button>
              </div>
            </div>
          </form>
          <div v-else-if="entry.review" class="flex items-start justify-between gap-3">
            <blockquote
              class="min-w-0 text-[15px] leading-normal wrap-break-word md:border-l-2 md:border-border md:py-1 md:pl-4 md:text-lg"
            >
              "{{ entry.review }}"
            </blockquote>
            <Button type="button" variant="ghost" class="-mr-2 h-11 shrink-0 text-muted-foreground md:h-9" @click="startReview"
              >고치기</Button
            >
          </div>
          <Button v-else type="button" variant="outline" class="h-11 self-start md:h-10" @click="startReview">한줄평 남기기</Button>
        </section>
      </div>

      <span class="relative text-xs text-muted-foreground md:hidden">출처 · {{ SOURCE_LABEL[entry.source] }}</span>

      <EntryDeleteDialog
        v-model:open="deleteOpen"
        :title="entry.game.title"
        :deleting="detail.saving.value"
        :error="detail.deleteError.value"
        @confirm="confirmDelete"
        @closed="moreButton?.$el?.focus()"
      />
    </template>
  </div>
</template>

<style scoped>
/* 본문 폭의 절반과 화면 폭(cqw)의 절반 차이만큼 양쪽으로 넓힌다 ─ LibraryView .wall-bleed와 같은 계산 */
.bleed {
  left: calc(50% - 50cqw);
  right: calc(50% - 50cqw);
}

/* 커버가 아래로 갈수록 배경색으로 사라진다 (목업 Detail backdropFade). 덮는 정도는 --fade-top
   맨 위 줄(뒤로 · 수정 · ⋮) 뒤만 더 진하게 덮는다 ─ 노란 커버에서 글자가 안 보였다 (2026-11-04 실제 폰에서 확인) */
.backdrop-fade {
  background: linear-gradient(
    180deg,
    color-mix(in oklab, var(--background) 80%, transparent) 0,
    color-mix(in oklab, var(--background) 80%, transparent) 3.5rem,
    color-mix(in oklab, var(--background) var(--fade-top), transparent) 6.5rem,
    color-mix(in oklab, var(--background) 75%, transparent) 55%,
    var(--background) 100%
  );
}
</style>
