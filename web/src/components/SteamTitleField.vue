<script setup lang="ts">
import { computed, ref } from 'vue'
import { X } from '@lucide/vue'
import { MIN_QUERY, useSteamSearch } from '@/composables/useSteamSearch'
import type { SteamApp } from '@/api/steam'
import { Input } from '@/components/ui/input'

// S-03 제목 칸 ─ 치면 Steam 후보가 뜨고, 고르지 않으면 적은 그대로 직접 등록한다 (DESIGN 3.3절)
const title = defineModel<string>('title', { required: true })
const steamApp = defineModel<SteamApp | null>('steamApp', { required: true })

const search = useSteamSearch()
const open = ref(false)
const active = ref(-1) // 키보드로 가리키는 후보. -1이면 없음

const showList = computed(() => open.value && (search.results.value.length > 0 || search.searched.value || search.failed.value))

function onInput(e: Event) {
  open.value = true
  active.value = -1
  // title이 아니라 입력칸에서 직접 읽는다 ─ Input 컴포넌트가 v-model을 다음 틱에 넘겨서,
  // 이 시점의 title은 아직 이전 값이다 (한 글자 전 값으로 검색이 나갔다)
  search.search((e.target as HTMLInputElement).value)
}

function pick(app: SteamApp) {
  steamApp.value = app
  title.value = app.name
  open.value = false
  search.clear()
}

function unpick() {
  steamApp.value = null
  title.value = ''
}

function onKeydown(e: KeyboardEvent) {
  const count = search.results.value.length
  if (e.key === 'Escape') {
    open.value = false
  } else if (e.key === 'ArrowDown' && count) {
    e.preventDefault() // 커서가 칸 끝으로 튀지 않게
    open.value = true
    active.value = (active.value + 1) % count
  } else if (e.key === 'ArrowUp' && count) {
    e.preventDefault()
    open.value = true
    active.value = (active.value - 1 + count) % count
  } else if (e.key === 'Enter' && open.value && active.value >= 0) {
    // 후보를 가리키고 있을 때만 고른다. 아니면 폼 제출로 흘려보낸다
    e.preventDefault()
    pick(search.results.value[active.value]!)
  }
}
</script>

<template>
  <!-- 고른 뒤 ─ 게임 이름 + 해제. 한국어 이름 · 커버는 SERVER가 채운다 -->
  <div
    v-if="steamApp"
    class="flex h-12 items-center justify-between gap-2 rounded-[10px] border border-brand-line bg-brand-tint pr-1 pl-3.5"
  >
    <span class="min-w-0 truncate text-base">
      <span class="font-semibold">{{ steamApp.name }}</span>
      <span class="ml-2 text-xs text-muted-foreground">Steam</span>
    </span>
    <button
      type="button"
      class="flex size-10 shrink-0 items-center justify-center rounded-lg text-muted-foreground hover:text-foreground"
      aria-label="고른 게임 해제"
      @click="unpick"
    >
      <X class="size-[18px]" aria-hidden="true" />
    </button>
  </div>

  <div v-else class="relative">
    <!-- 접근성: 입력칸이 후보 목록을 조종한다는 것을 화면 읽기 프로그램에 알린다 -->
    <Input
      id="title"
      v-model="title"
      type="text"
      role="combobox"
      autocomplete="off"
      maxlength="200"
      aria-autocomplete="list"
      aria-controls="title-options"
      aria-describedby="title-help"
      :aria-expanded="showList"
      :aria-activedescendant="active >= 0 ? `title-option-${active}` : undefined"
      placeholder="예: Baldur's Gate 3"
      class="h-12 bg-card text-base"
      @input="onInput"
      @keydown="onKeydown"
      @blur="open = false"
    />

    <div
      v-if="showList"
      class="absolute top-full right-0 left-0 z-20 mt-1 overflow-hidden rounded-[10px] border border-border bg-card shadow-lg"
    >
      <!-- mousedown.prevent ─ 누르는 순간 입력칸이 blur되어 목록이 먼저 닫히는 것을 막는다 -->
      <ul v-if="search.results.value.length" id="title-options" role="listbox" class="max-h-[320px] overflow-y-auto">
        <li
          v-for="(app, i) in search.results.value"
          :id="`title-option-${i}`"
          :key="app.appid"
          role="option"
          :aria-selected="i === active"
          class="cursor-pointer truncate px-3.5 py-2.5 text-[15px]"
          :class="i === active ? 'bg-secondary' : 'hover:bg-secondary'"
          @mousedown.prevent="pick(app)"
        >
          {{ app.name }}
        </li>
      </ul>
      <p v-else-if="search.failed.value" class="px-3.5 py-3 text-sm text-muted-foreground">
        지금은 검색할 수 없어요. 제목을 적어 직접 등록할 수 있어요
      </p>
      <p v-else class="px-3.5 py-3 text-sm text-muted-foreground">찾는 게임이 없어요. 이 제목 그대로 직접 등록할 수 있어요</p>
    </div>
  </div>

  <span id="title-help" class="text-xs text-muted-foreground">
    영어 제목으로 찾아 주세요 ({{ MIN_QUERY }}글자부터). 없으면 그대로 적어 직접 등록해요
  </span>
</template>
