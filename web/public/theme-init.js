// 앱(Vue)이 뜨기 전에 테마부터 입힌다 ─ 늦게 입히면 다크를 고른 사람에게 흰 화면이 번쩍인다
// index.html에 직접 쓰지 않고 파일로 뺀다 ─ 운영 CSP가 인라인 스크립트를 막는다 (deploy/Caddyfile)
// module이 아닌 일반 script라 화면을 그리기 전에 실행된다
// 규칙은 src/lib/theme.ts와 같다. 바꿀 때는 둘 다 고친다 (키 이름 'pl-theme' 포함)
;(function () {
  var pref = 'system'
  try {
    var saved = localStorage.getItem('pl-theme')
    if (saved === 'dark' || saved === 'light' || saved === 'system') pref = saved
  } catch (e) {}
  var dark = pref === 'dark' || (pref === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)
  document.documentElement.classList.toggle('dark', dark)
  document.documentElement.style.colorScheme = dark ? 'dark' : 'light'
})()
