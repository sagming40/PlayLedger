import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

// 주소 1개당 화면 1개 ─ 건물 1층 로비의 "층별 안내판"
const routes: RouteRecordRaw[] = [
  // 아무런 주소도 없이 들어오면 라이브러리(홈)로 돌려보낸다
  { path: '/', redirect: '/library' },

  {
    path: '/login',
    name: 'login',
    // 이 화면을 처음 열 때 비로소 파일을 받아온다 (아래 설명)
    component: () => import('@/views/LoginView.vue'),
  },
  {
    path: '/library',
    name: 'library',
    component: () => import('@/views/LibraryView.vue'),
  },
  {
    path: '/stats',
    name: 'stats',
    component: () => import('@/views/StatsView.vue'),
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('@/views/SettingsView.vue'),
  },

  // 위 주소 중 어디에도 해당되지 않는 주소는 전부 이 곳으로 떨어진다
  // 반드시 목록 맨 끝 부분에 둘 것 ─ 위에서부터 훑어 내려오다 먼저 걸리는 주소를 사용한다
  { path: '/:pathMatch(.*)*', redirect: '/library' },
]

const router = createRouter({
  // 주소를 /library의 형태처럼 깔끔하게 표기한다 (# 없이)
  history: createWebHistory(),
  routes,
})

export default router
