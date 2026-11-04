<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ChevronLeft } from '@lucide/vue'
import { createEntry } from '@/api/entries'
import type { EntryStatus } from '@/api/entries'
import { ApiError } from '@/api/errors'
import type { SteamApp } from '@/api/steam'
import EntryFormFields from '@/components/EntryFormFields.vue'
import FormField from '@/components/FormField.vue'
import SteamTitleField from '@/components/SteamTitleField.vue'
import { Button } from '@/components/ui/button'
import { buildCreateBody, issuesMessage } from '@/lib/entry-form'
import { showToast } from '@/lib/toast'

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

const submitting = ref(false)
const errorMessage = ref('')

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

async function onSubmit() {
  // 버튼이 비활성이어도 엔터로 들어올 수 있어서 한 번 더 막는다
  if (!canSubmit.value || !body.value) return

  submitting.value = true
  errorMessage.value = ''
  try {
    await createEntry(body.value)
    showToast('등록했어요')
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

      <EntryFormFields
        v-model:status="status"
        v-model:genre-ids="genreIds"
        v-model:purchased-at="purchasedAt"
        v-model:price="price"
        v-model:hours="hours"
        v-model:rating="rating"
        v-model:review="review"
      >
        <template #genre-hint>
          <span v-if="steamApp" class="text-xs text-muted-foreground">
            Steam 장르가 있으면 그것이 먼저 쓰여요. 고른 장르는 Steam에 맞는 장르가 없을 때 쓰여요
          </span>
        </template>
      </EntryFormFields>

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
