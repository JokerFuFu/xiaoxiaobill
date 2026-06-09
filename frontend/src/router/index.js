import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  { path: '/login', name: 'login', component: () => import('@/views/Login.vue'), meta: { bare: true, public: true } },
  { path: '/', name: 'home', component: () => import('@/views/Home.vue') },
  { path: '/yearly', name: 'yearly', component: () => import('@/views/Yearly.vue') },
  { path: '/monthly', name: 'monthly', component: () => import('@/views/Monthly.vue') },
  { path: '/category', name: 'category', component: () => import('@/views/Category.vue') },
  { path: '/time', name: 'time', component: () => import('@/views/Time.vue') },
  { path: '/insights', name: 'insights', component: () => import('@/views/Insights.vue') },
  { path: '/channels', name: 'channels', component: () => import('@/views/Channels.vue') },
  { path: '/transactions', name: 'transactions', component: () => import('@/views/Transactions.vue') },
  { path: '/transfers', name: 'transfers', component: () => import('@/views/Transactions.vue') },
  { path: '/ai', name: 'ai', component: () => import('@/views/AI.vue') },
  { path: '/admin', name: 'admin', component: () => import('@/views/Admin.vue'), meta: { admin: true } },
  { path: '/settings', name: 'settings', component: () => import('@/views/Settings.vue') },
  { path: '/about-author', name: 'about-author', component: () => import('@/views/AboutAuthor.vue') }
]

const router = createRouter({
  history: createWebHistory('/'),
  routes
})

// 全局守卫:未登录跳登录页;管理员页校验权限
router.beforeEach(async (to) => {
  const auth = useAuthStore()
  await auth.ensureLoaded()
  if (to.meta.public) {
    if (to.path === '/login' && auth.isAuthenticated) return { path: '/' }
    return true
  }
  if (!auth.isAuthenticated) {
    return { path: '/login', query: to.path !== '/' ? { redirect: to.fullPath } : {} }
  }
  if (to.meta.admin && !auth.isAdmin) {
    return { path: '/' }
  }
  return true
})

export default router
