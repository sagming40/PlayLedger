<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { titleInitials } from '@/lib/entry-display'

// 게임 커버 ─ 주소가 없거나 깨지면 제목 앞 두 글자로 대체한다 (DESIGN 4.4절)
// 주소에 해시가 들어 있어 나중에 깨질 수 있다 (decisions/0008)
const props = defineProps<{
  title: string
  coverUrl: string | null
}>()

const broken = ref(false)
// 목록이 다시 그려져 다른 게임을 받으면 실패 표시를 지운다
watch(
  () => props.coverUrl,
  () => (broken.value = false),
)

const showImage = computed(() => props.coverUrl !== null && !broken.value)
</script>

<template>
  <!-- 제목이 옆에 글자로 있으므로 그림은 장식이다 (alt 비움) -->
  <img
    v-if="showImage"
    :src="coverUrl!"
    alt=""
    loading="lazy"
    referrerpolicy="no-referrer"
    class="size-full object-cover"
    @error="broken = true"
  />
  <slot v-else :initials="titleInitials(title)" />
</template>
