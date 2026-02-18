import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import DashboardLayout from '@/layouts/DashboardLayout.vue'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/predicao',
  },
  {
    path: '/',
    component: DashboardLayout,
    children: [
      {
        path: 'predicao',
        name: 'predicao',
        component: () => import('@/views/PredicaoView.vue'),
        meta: { titulo: 'Predição OER' },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/predicao',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(_to, _from, savedPosition) {
    return savedPosition ?? { top: 0 }
  },
})

router.afterEach((to) => {
  const titulo = to.meta.titulo as string | undefined
  document.title = titulo ? `Nanoxus - ${titulo}` : 'Nanoxus'
})

export default router
