import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import AppLayout from '@/components/AppLayout.vue'

// meta에 어떤 값이 들어갈 수 있는지 TypeScript에게 알려준다
// 그렇지 않으면 route.meta.title 사용 시 값을 찾지 못해 에러를 띄운다
declare module 'vue-router' {
  interface RouteMeta {
    title?: string
  }
}

// 주소 1개당 화면 1개 ─ 건물 1층 로비의 "층별 안내판"
const routes: RouteRecordRaw[] = [
  // 레이아웃 바깥 ─ 사이드바/하단 탭이 없는 전체 화면
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
  },

  // 레이아웃 안쪽 ─ 부모가 껍데기를 그리고 자식이 그 안에 들어간다
  {
    path: '/',
    component: AppLayout,
    children: [
      // 자식 경로에는 앞 슬래시를 붙이지 않는다 (앞 슬래시를 붙이면 부모를 무시하고 최상위 경로가 된다)
      { path: '', redirect: '/library' },
      {
        path: 'library',
        name: 'library',
        meta: { title: '라이브러리' },
        component: () => import('@/views/LibraryView.vue'),
      },
      {
        path: 'stats',
        name: 'stats',
        meta: { title: '통계' },
        component: () => import('@/views/StatsView.vue'),
      },
      {
        path: 'settings',
        name: 'settings',
        meta: { title: '설정' },
        component: () => import('@/views/SettingsView.vue'),
      },
    ],
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
