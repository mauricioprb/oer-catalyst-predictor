import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import DashboardLayout from '@/layouts/DashboardLayout.vue'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/laboratorio',
  },
  {
    path: '/',
    component: DashboardLayout,
    children: [
      {
        path: 'laboratorio',
        name: 'laboratorio',
        component: () => import('@/views/LaboratorioView.vue'),
        meta: { titulo: 'Laboratório — Predição OER' },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/laboratorio',
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
