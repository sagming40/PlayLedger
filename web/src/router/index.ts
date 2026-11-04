import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { nextTick } from 'vue'
import AppLayout from '@/components/AppLayout.vue'
import { handleAppError } from '@/lib/app-errors'
import { rememberLibrary } from '@/lib/library-return'
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
  // 레이아웃 바깥 ─ 메뉴 띠/하단 탭이 없는 전체 화면
  {
    path: '/login',
    name: 'login',
    meta: { public: true, title: '로그인' },
    component: () => import('@/views/LoginView.vue'),
  },
  {
    // 가입 전에도 읽을 수 있어야 한다 (DESIGN 3.6절)
    path: '/privacy',
    name: 'privacy',
    meta: { public: true, title: '개인정보 안내' },
    component: () => import('@/views/PrivacyView.vue'),
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
      // S-03 · S-04는 라이브러리의 하위 화면이라 주소도 /library 아래에 둔다 (DESIGN 2.1절)
      // new를 :id보다 먼저 ─ 위에서부터 맞춰 보므로 뒤에 두면 'new'가 id로 읽힌다
      {
        path: 'library/new',
        name: 'entry-new',
        meta: { title: '게임 등록', ownTitle: true },
        component: () => import('@/views/EntryNewView.vue'),
      },
      {
        // (\\d+) ─ 숫자만 받는다. 문자열 안이라 역슬래시를 두 번 쓴다
        path: 'library/:id(\\d+)',
        name: 'entry-detail',
        // 제목 자리에 게임 이름을 직접 그린다 (DESIGN 3.4절)
        meta: { title: '게임 상세', ownTitle: true },
        component: () => import('@/views/EntryDetailView.vue'),
      },
      {
        path: 'library/:id(\\d+)/edit',
        name: 'entry-edit',
        meta: { title: '게임 수정', ownTitle: true },
        component: () => import('@/views/EntryEditView.vue'),
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
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    meta: { public: true, title: '페이지를 찾을 수 없어요' },
    component: () => import('@/views/NotFoundView.vue'),
  },
]

const router = createRouter({
  // 주소를 /library의 형태처럼 깔끔하게 표기한다 (# 없이)
  history: createWebHistory(),
  routes,
  // 뒤로가기는 보던 자리로, 새 화면은 맨 위로. 필터처럼 주소 뒤쪽만 바뀌면 그대로 둔다
  scrollBehavior(to, from, saved) {
    if (saved) return saved
    return to.path === from.path ? false : { top: 0 }
  },
})

// 모든 화면 이동이 이 문지기를 먼저 거친다 (guard.ts)
router.beforeEach(authGuard)

// 화면 조각을 받지 못했을 때 ─ 새 버전 배포 직후 열어 둔 탭 (lib/app-errors.ts)
router.onError((error, to) => handleAppError(error, to.fullPath))

router.afterEach((to, from) => {
  document.title = to.meta.title ? `${to.meta.title} · PLAYLEDGER` : 'PLAYLEDGER'
  if (to.name === 'library') rememberLibrary(to.fullPath)

  // 화면을 옮기면 키보드 · 화면 읽기 프로그램의 위치도 새 화면으로 옮긴다
  // 그대로 두면 사라진 링크 자리에서 맴돈다. 처음 열 때와 필터 변경은 빼고
  if (from.matched.length === 0 || to.path === from.path) return
  nextTick(() => {
    const main = document.querySelector('main')
    main?.setAttribute('tabindex', '-1')
    main?.focus({ preventScroll: true })
  })
})

export default router
