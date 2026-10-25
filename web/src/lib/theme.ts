// 테마(다크 · 라이트) 판정 규칙 (UI_DESIGN 4.4절, F-24)
// 브라우저 객체를 직접 만지지 않는 순수 함수만 둔다 ─ 테스트에서 가짜 저장소 · 가짜 <html>로 검증한다
// index.html의 인라인 스크립트가 같은 규칙을 한 번 더 적는다 (앱이 뜨기 전에 써야 해서). 바꿀 때는 둘 다 고친다

export type ThemePreference = 'system' | 'dark' | 'light'
export type ResolvedTheme = 'dark' | 'light'

// localStorage 키. 이 앱이 브라우저에 남기는 유일한 값이다 (MILESTONES M2 완료 기준 7번)
export const THEME_KEY = 'pl-theme'

const VALID: readonly ThemePreference[] = ['system', 'dark', 'light']

/**
 * 저장된 선택을 읽는다. 없거나 이상한 값이면 'system'
 *
 * 사생활 보호 모드 등에서는 localStorage에 접근만 해도 예외가 난다 ─ 그때도 'system'으로 계속 간다
 * 테마는 있으면 좋은 것이지, 이것 때문에 앱이 멈추면 안 된다
 */
export function readPreference(storage: Pick<Storage, 'getItem'> | undefined): ThemePreference {
  try {
    const saved = storage?.getItem(THEME_KEY)
    return VALID.includes(saved as ThemePreference) ? (saved as ThemePreference) : 'system'
  } catch {
    return 'system'
  }
}

/** 선택을 저장한다. 저장이 막혀 있어도 예외를 밖으로 내보내지 않는다 (이번 방문 동안은 적용된다) */
export function writePreference(storage: Pick<Storage, 'setItem'> | undefined, pref: ThemePreference): void {
  try {
    storage?.setItem(THEME_KEY, pref)
  } catch {
    // 저장 실패 ─ 새로고침하면 시스템 설정으로 돌아갈 뿐이다
  }
}

/** 선택 + 지금 OS 설정 → 실제로 칠할 테마 */
export function resolveTheme(pref: ThemePreference, systemDark: boolean): ResolvedTheme {
  if (pref === 'system') return systemDark ? 'dark' : 'light'
  return pref
}

/**
 * <html>에 테마를 입힌다
 * .dark ─ style.css의 다크 토큰이 켜진다
 * color-scheme ─ 스크롤바 · 날짜 입력칸 · select 같은 브라우저 기본 부품도 같은 테마로 그려진다
 */
export function applyTheme(
  root: { classList: { toggle(name: string, force?: boolean): unknown }; style: { colorScheme: string } },
  theme: ResolvedTheme,
): void {
  root.classList.toggle('dark', theme === 'dark')
  root.style.colorScheme = theme
}
