import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { applyTheme, readPreference, resolveTheme, THEME_KEY, writePreference } from './theme'
import { useThemeStore } from '@/stores/theme'

// 테마 전환 (F-24, UI_DESIGN 4.4절)
// OS 설정 변경 · 저장소 차단은 브라우저에서 매번 만들기 번거로워 여기서 고정한다

function fakeStorage(initial: Record<string, string> = {}) {
  const data = { ...initial }
  return {
    data,
    getItem: (k: string) => (k in data ? data[k]! : null),
    setItem: (k: string, v: string) => {
      data[k] = v
    },
  }
}

function fakeRoot() {
  const classes = new Set<string>()
  return {
    classes,
    classList: {
      toggle(name: string, force?: boolean) {
        if (force ?? !classes.has(name)) classes.add(name)
        else classes.delete(name)
      },
    },
    style: { colorScheme: '' },
  }
}

// OS 설정을 테스트가 바꿀 수 있는 가짜 window
function fakeWindow(systemDark: boolean, storage = fakeStorage()) {
  const listeners: ((e: { matches: boolean }) => void)[] = []
  const media = {
    matches: systemDark,
    addEventListener: (_: string, fn: (e: { matches: boolean }) => void) => listeners.push(fn),
  }
  return {
    localStorage: storage,
    matchMedia: vi.fn(() => media),
    // OS를 다크 ↔ 라이트로 바꾼 것처럼 알린다
    flip(dark: boolean) {
      media.matches = dark
      listeners.forEach((fn) => fn({ matches: dark }))
    },
  }
}

describe('판정 규칙', () => {
  it.each([
    ['system', true, 'dark'],
    ['system', false, 'light'],
    ['dark', false, 'dark'],
    ['light', true, 'light'],
  ] as const)('선택 %s + OS 다크 %s → %s', (pref, systemDark, expected) => {
    expect(resolveTheme(pref, systemDark)).toBe(expected)
  })

  it('저장된 값이 없거나 이상하면 system', () => {
    expect(readPreference(fakeStorage())).toBe('system')
    expect(readPreference(fakeStorage({ [THEME_KEY]: 'blue' }))).toBe('system')
  })

  it('저장소 접근이 막혀 있어도(사생활 보호 모드) 멈추지 않는다', () => {
    const blocked = {
      getItem: () => {
        throw new Error('SecurityError')
      },
      setItem: () => {
        throw new Error('SecurityError')
      },
    }
    expect(readPreference(blocked)).toBe('system')
    expect(() => writePreference(blocked, 'dark')).not.toThrow()
  })

  it('다크를 입히면 .dark와 color-scheme가 함께 바뀐다', () => {
    const root = fakeRoot()
    applyTheme(root, 'dark')
    expect(root.classes.has('dark')).toBe(true)
    expect(root.style.colorScheme).toBe('dark')
    applyTheme(root, 'light')
    expect(root.classes.has('dark')).toBe(false)
    expect(root.style.colorScheme).toBe('light')
  })
})

describe('테마 스토어', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it("'시스템'이면 OS 설정이 바뀔 때 새로고침 없이 따라간다 (M2 완료 기준)", () => {
    const win = fakeWindow(false)
    const root = fakeRoot()
    const theme = useThemeStore()
    theme.init(root as unknown as HTMLElement, win as unknown as Window)
    expect(root.classes.has('dark')).toBe(false)

    win.flip(true)
    expect(root.classes.has('dark')).toBe(true)
    win.flip(false)
    expect(root.classes.has('dark')).toBe(false)
  })

  it("'다크'를 고르면 저장되고, OS가 라이트로 바뀌어도 다크를 유지한다", () => {
    const storage = fakeStorage()
    const win = fakeWindow(true, storage)
    const root = fakeRoot()
    const theme = useThemeStore()
    theme.init(root as unknown as HTMLElement, win as unknown as Window)

    theme.setPreference('dark', win as unknown as Window)
    win.flip(false)

    expect(storage.data[THEME_KEY]).toBe('dark')
    expect(root.classes.has('dark')).toBe(true)
  })

  it('다시 열면(새로고침) 저장된 선택으로 시작한다', () => {
    const win = fakeWindow(true, fakeStorage({ [THEME_KEY]: 'light' }))
    const root = fakeRoot()
    const theme = useThemeStore()
    theme.init(root as unknown as HTMLElement, win as unknown as Window)

    expect(theme.preference).toBe('light')
    expect(root.classes.has('dark')).toBe(false)
  })
})
