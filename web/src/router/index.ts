import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import AppLayout from '@/components/AppLayout.vue'
import { authGuard } from './guard'

// meta에 어떤 값이 들어갈 수 있는지 TypeScript에게 알려준다
// 그렇지 않으면 route.meta.title 사용 시 값을 찾지 못해 에러를 띄운다
declare module 'vue-router' {
  interface RouteMeta {
    title?: string
    // 로그인 없이 들어올 수 있는 화면. 표시가 없으면 전부 보호된 화면이다
    // 반대(보호할 화면에 표시)로 두면, 새 화면에 표시를 빠뜨리는 순간 아무나 들어온다
    public?: boolean
    // 화면이 제목을 직접 그린다 (S-02 포스터 벽 안의 제목). 표시가 있으면 레이아웃의 공통 제목을 숨긴다
    ownTitle?: boolean
  }
}

// 주소 1개당 화면 1개 ─ 건물 1층 로비의 "층별 안내판"
const routes: RouteRecordRaw[] = [
  // 레이아웃 바깥 ─ 사이드바/하단 탭이 없는 전체 화면
  {
    path: '/login',
    name: 'login',
    meta: { public: true },
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
        meta: { title: '라이브러리', ownTitle: true },
        component: () => import('@/views/LibraryView.vue'),
      },
      // S-03 · S-04는 라이브러리의 하위 화면이라 주소도 /library 아래에 둔다 (UI_DESIGN 2.1절)
      // new를 :id보다 먼저 ─ 위에서부터 맞춰 보므로 뒤에 두면 'new'가 id로 읽힌다
      // 화면은 다음 작업(S-03 · M3 S-04)에서 채운다. 지금은 목록 카드 · 등록 버튼이 갈 자리만 있다
      {
        path: 'library/new',
        name: 'entry-new',
        meta: { title: '게임 등록' },
        component: () => import('@/views/EntryNewView.vue'),
      },
      {
        // (\\d+) ─ 숫자만 받는다. 문자열 안이라 역슬래시를 두 번 쓴다
        path: 'library/:id(\\d+)',
        name: 'entry-detail',
        meta: { title: '게임 상세' },
        component: () => import('@/views/EntryDetailView.vue'),
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

// 모든 화면 이동이 이 문지기를 먼저 거친다 (guard.ts)
router.beforeEach(authGuard)

export default router
