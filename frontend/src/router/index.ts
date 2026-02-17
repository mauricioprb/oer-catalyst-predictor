import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import DashboardLayout from '@/layouts/DashboardLayout.vue'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/dashboard',
  },
  {
    path: '/dashboard',
    component: DashboardLayout,
    children: [
      {
        path: '',
        name: 'dashboard',
        component: () => import('@/views/DashboardView.vue'),
        meta: { titulo: 'Visão Geral' },
      },
      {
        path: 'analise',
        name: 'analise',
        component: () => import('@/views/AnaliseView.vue'),
        meta: { titulo: 'Análise de Imagem' },
      },
      {
        path: 'treinamento',
        name: 'treinamento',
        component: () => import('@/views/TreinamentoView.vue'),
        meta: { titulo: 'Treinamento' },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/dashboard',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(_to, _from, savedPosition) {
    return savedPosition ?? { top: 0 }
  },
})

export default router
