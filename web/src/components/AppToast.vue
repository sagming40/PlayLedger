<script setup lang="ts">
import { CircleCheck } from '@lucide/vue'
import { AnimatePresence, Motion, MotionConfig } from 'motion-v'
import { toast } from '@/lib/toast'

// 저장 성공 알림 (DESIGN 6장). 비유: 잠깐 올라왔다 내려가는 쪽지
// reduced-motion="user" ─ OS의 "동작 줄이기"를 켠 사람에게는 움직임을 빼고 흐려지기만 한다
</script>

<template>
  <!-- 화면 읽기 프로그램은 "이미 있던 칸의 글자가 바뀌는 것"만 읽는다 ─ 칸은 항상 두고 안쪽만 바꾼다
       pointer-events-none ─ 잠깐 뜨는 알림이 아래 버튼을 가로막지 않게
       bottom-20: 모바일 하단 탭(64px) 위 -->
  <div role="status" aria-live="polite" class="pointer-events-none fixed inset-x-0 bottom-20 z-40 flex justify-center px-4 md:bottom-8">
    <MotionConfig reduced-motion="user">
      <AnimatePresence mode="wait">
        <Motion
          v-if="toast"
          :key="toast.id"
          :initial="{ opacity: 0, y: 12 }"
          :animate="{ opacity: 1, y: 0 }"
          :exit="{ opacity: 0, y: 6 }"
          :transition="{ duration: 0.18, ease: 'easeOut' }"
          class="flex h-11 items-center gap-2 rounded-[10px] border border-border bg-popover px-4 text-sm font-semibold text-popover-foreground shadow-md"
        >
          <CircleCheck class="size-[18px] text-status-cleared" aria-hidden="true" />
          {{ toast.text }}
        </Motion>
      </AnimatePresence>
    </MotionConfig>
  </div>
</template>
