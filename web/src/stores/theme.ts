import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import {
  applyTheme,
  readPreference,
  resolveTheme,
  writePreference,
  type ThemePreference,
} from '@/lib/theme'

// 테마 선택 (S-06 화면 테마, F-24)
// 판정 규칙은 lib/theme.ts, 이 스토어는 "지금 무엇을 골랐고 OS가 어떤 상태인가"만 들고 있다
export const useThemeStore = defineStore('theme', () => {
  const preference = ref<ThemePreference>('system')
  const systemDark = ref(false)

  // 실제로 칠해진 테마. 화면이 "지금 다크인가"를 알아야 할 때 쓴다
  const resolved = computed(() => resolveTheme(preference.value, systemDark.value))

  let root: HTMLElement | null = null

  function paint() {
    if (root) applyTheme(root, resolved.value)
  }

  /**
   * 앱 시작 시 한 번 부른다 (main.ts)
   * index.html의 인라인 스크립트가 이미 칠해 둔 상태를 이어받고, 이후 OS 설정 변경을 따라간다
   */
  function init(target: HTMLElement = document.documentElement, win: Window = window) {
    root = target
    preference.value = readPreference(win.localStorage)

    const media = win.matchMedia('(prefers-color-scheme: dark)')
    systemDark.value = media.matches
    // '시스템'을 고른 동안 OS를 다크 ↔ 라이트로 바꾸면 새로고침 없이 따라간다 (M2 완료 기준)
    media.addEventListener('change', (e) => {
      systemDark.value = e.matches
      paint()
    })
    paint()
  }

  function setPreference(pref: ThemePreference, win: Window = window) {
    preference.value = pref
    writePreference(win.localStorage, pref)
    paint()
  }

  return { preference, resolved, init, setPreference }
})
