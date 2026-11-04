// 저장 성공 알림 (DESIGN 6장)
// 화면을 옮겨도 살아 있어야 해서 화면 밖에 둔다 ─ 저장하자마자 상세 · 목록으로 넘어가므로 화면이 들고 있으면 함께 사라진다
// 실패는 여기로 오지 않는다. 실패 문구는 그 칸 옆에 둔다 (DESIGN 3.1절 "알림창 사용 안 함")

import { ref } from 'vue'

const VISIBLE_MS = 2500

export interface Toast {
  id: number // 같은 문구가 또 떠도 새 알림으로 다시 움직이게 한다
  text: string
}

export const toast = ref<Toast | null>(null)

let nextId = 1
let timer: ReturnType<typeof setTimeout> | undefined

/** 알림은 한 번에 하나 ─ 쌓아 두면 이미 지난 일을 뒤늦게 알리게 된다. 새 알림이 앞 알림을 바꾼다 */
export function showToast(text: string) {
  clearTimeout(timer)
  toast.value = { id: nextId++, text }
  timer = setTimeout(() => (toast.value = null), VISIBLE_MS)
}
