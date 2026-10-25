import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './style.css'
import App from './App.vue'
import router from './router'
import { useThemeStore } from './stores/theme'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)

// 테마는 라우터보다 먼저 ─ 로그인 화면을 포함해 어떤 화면이 그려지기 전에 OS 설정 추적을 시작한다
useThemeStore(pinia).init()

app.use(router).mount('#app')
