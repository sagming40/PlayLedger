<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ChevronLeft } from '@lucide/vue'
import { useEntryEdit } from '@/composables/useEntryEdit'
import { useLeaveGuard } from '@/composables/useLeaveGuard'
import EntryFormFields from '@/components/EntryFormFields.vue'
import FormField from '@/components/FormField.vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

// S-03 게임 수정 (DESIGN 3.3절) ─ 칸은 등록 화면과 같다(EntryFormFields). 제목은 고칠 수 없다 (DATA_MODEL 2.6절)
const route = useRoute()
const router = useRouter()
const edit = useEntryEdit()
useLeaveGuard(() => edit.isDirty.value)

// 주소 규칙이 숫자만 받으므로(router (\d+)) Number가 NaN이 되지 않는다
watch(
  () => route.params.id,
  (id) => {
    if (typeof id === 'string') edit.load(Number(id))
  },
  { immediate: true },
)

const form = computed(() => edit.form.value)
// 직접 등록한 게임은 내 것이라 장르를 언제든 바꾼다. Steam 게임은 다 같이 보는 행이라 고정 (decisions/0011)
const isSteamGame = computed(() => edit.entry.value?.game.steam_appid !== null)

// 상세로 돌아간다. 상세에서 왔으면 뒤로 간다 ─ 새로 이동하면 방문 기록에 상세 · 수정이 쌓여 뒤로가기가 이 폼으로 돌아온다
// 주소를 직접 쳐서 들어왔으면 돌아갈 상세가 기록에 없으니 이 자리를 상세로 바꾼다
function backToDetail() {
  const detail = { name: 'entry-detail', params: { id: route.params.id } }
  if (window.history.state?.back === router.resolve(detail).fullPath) router.back()
  else router.replace(detail)
}

async function onSubmit() {
  if (await edit.submit()) backToDetail()
}
</script>

<template>
  <div class="flex max-w-190 flex-col gap-6">
    <!-- custom ─ RouterLink가 스스로 이동하지 않게 한다. 그냥 @click을 달면 자기 이동과 backToDetail이 둘 다 돈다 -->
    <RouterLink v-slot="{ href }" :to="{ name: 'entry-detail', params: { id: route.params.id } }" custom>
      <a
        :href="href"
        class="inline-flex h-11 items-center gap-1.5 self-start text-sm text-muted-foreground hover:text-foreground"
        @click.prevent="backToDetail"
      >
        <ChevronLeft class="size-4.5" aria-hidden="true" />
        게임 상세
      </a>
    </RouterLink>

    <!-- 처음 불러오는 중 ─ 자리만 잡는다 (DESIGN 6장 뼈대) -->
    <div v-if="edit.loading.value && !form" role="status" aria-label="게임 정보를 불러오는 중" class="flex flex-col gap-4">
      <div class="h-10 w-48 animate-pulse rounded bg-secondary" />
      <div class="h-12 w-full animate-pulse rounded-[10px] bg-secondary" />
      <div class="h-11 w-2/3 animate-pulse rounded-[10px] bg-secondary" />
    </div>

    <!-- 없거나 남의 기록 ─ 둘을 구분하지 않는다 (ARCHITECTURE 3.8절) -->
    <div v-else-if="edit.notFound.value" role="alert" class="flex flex-col items-center gap-3 py-24 text-center">
      <h1 class="text-[22px] font-bold">게임을 찾을 수 없어요</h1>
      <p class="text-[15px] text-muted-foreground">지워졌거나 주소가 잘못됐어요</p>
      <Button as-child variant="outline" class="mt-2 h-11">
        <RouterLink :to="{ name: 'library' }">라이브러리로</RouterLink>
      </Button>
    </div>

    <!-- 네트워크 · 서버 오류 ─ 안내 + 다시 시도 (DESIGN 6장) -->
    <div v-else-if="edit.loadError.value" role="alert" class="flex flex-col items-center gap-3 py-24 text-center">
      <p class="text-[15px]">{{ edit.loadError.value }}</p>
      <Button variant="outline" class="h-11" @click="edit.load(Number(route.params.id))">다시 시도</Button>
    </div>

    <template v-else-if="form && edit.entry.value">
      <h1 class="text-[34px] font-extrabold tracking-tight">게임 수정</h1>

      <form class="flex flex-col gap-6.5" @submit.prevent="onSubmit">
        <FormField id="title" label="제목" help="제목은 고칠 수 없어요. 잘못 등록했다면 삭제하고 다시 등록해 주세요">
          <Input
            id="title"
            :model-value="edit.entry.value.game.title"
            readonly
            aria-describedby="title-help"
            class="h-12 bg-secondary text-[15px] text-muted-foreground"
          />
        </FormField>

        <EntryFormFields
          v-model:status="form.status"
          v-model:genre-ids="form.genreIds"
          v-model:purchased-at="form.purchasedAt"
          v-model:price="form.price"
          v-model:hours="form.hours"
          v-model:rating="form.rating"
          v-model:review="form.review"
          :fixed-genres="isSteamGame ? edit.entry.value.game.genres : []"
        >
          <template v-if="isSteamGame" #genre-hint>
            <span class="text-xs text-muted-foreground">아직 장르가 없는 게임이에요. 한 번 저장한 장르는 바꿀 수 없어요</span>
          </template>
        </EntryFormFields>

        <p v-if="edit.errorMessage.value" role="alert" class="text-sm text-destructive">{{ edit.errorMessage.value }}</p>

        <div class="flex justify-end gap-2.5 border-t border-border pt-2">
          <Button type="button" variant="outline" class="mt-2 h-11.5 px-4.5 text-[15px]" @click="backToDetail">취소</Button>
          <Button type="submit" class="mt-2 h-11.5 px-5.5 text-[15px] font-bold" :disabled="!edit.canSubmit.value">
            {{ edit.submitting.value ? '저장 중…' : '저장' }}
          </Button>
        </div>
      </form>
    </template>
  </div>
</template>
