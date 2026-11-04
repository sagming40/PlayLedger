<script setup lang="ts">
import { computed, ref } from 'vue'
import { CalendarDays } from '@lucide/vue'
import { getLocalTimeZone, today, type DateValue } from '@internationalized/date'
import { Button } from '@/components/ui/button'
import { Calendar } from '@/components/ui/calendar'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { fromCalendarDate, toCalendarDate, yearRange } from '@/lib/date-field'

// 날짜 칸 ─ 버튼을 누르면 달력이 뜬다 (DESIGN 3.3절). 값은 글자 'YYYY-MM-DD' 그대로 오간다
// 바깥 라벨의 for가 가리키도록 id를 버튼에 단다
defineProps<{ id: string }>()
const model = defineModel<string>({ required: true })

const open = ref(false)
const selected = computed(() => toCalendarDate(model.value))
const now = today(getLocalTimeZone())
const years = computed(() => yearRange(now, selected.value))

function pick(value: DateValue | undefined) {
  model.value = fromCalendarDate(value)
  if (value) open.value = false
}

function clear() {
  model.value = ''
  open.value = false
}
</script>

<template>
  <Popover v-model:open="open">
    <PopoverTrigger as-child>
      <Button
        :id="id"
        type="button"
        variant="outline"
        class="h-12 w-full justify-between bg-card px-3 text-[15px] font-normal dark:bg-card"
        :class="selected ? '' : 'text-muted-foreground'"
      >
        {{ selected ? model : '날짜 선택' }}
        <CalendarDays class="size-4 text-muted-foreground" aria-hidden="true" />
      </Button>
    </PopoverTrigger>
    <PopoverContent align="start" class="w-auto p-0">
      <!-- 오래전 구매일을 화살표로 넘기지 않게 연 · 월을 고르는 칸을 켠다 -->
      <!-- 같은 날을 다시 눌러도 지워지지 않는다 ─ 지우기는 아래 버튼으로만 -->
      <Calendar
        :model-value="selected"
        :default-placeholder="selected ?? now"
        :year-range="years"
        layout="month-and-year"
        locale="ko-KR"
        prevent-deselect
        initial-focus
        @update:model-value="pick"
      />
      <div v-if="selected" class="flex justify-end border-t border-border p-2">
        <Button type="button" variant="ghost" class="h-9 text-[13px] text-muted-foreground" @click="clear">지우기</Button>
      </div>
    </PopoverContent>
  </Popover>
</template>
