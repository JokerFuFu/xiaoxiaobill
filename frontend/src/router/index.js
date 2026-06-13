import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  { path: '/login', name: 'login', component: () => import('@/views/Login.vue'), meta: { bare: true, public: true } },
  { path: '/', name: 'home', component: () => import('@/views/Home.vue') },
  // 五个分析整合到「数据分析」单页(二级标签);旧路由重定向保兼容
  { path: '/analysis', name: 'analysis', component: () => import('@/views/Analysis.vue') },
  { path: '/yearly', redirect: '/analysis?tab=yearly' },
  { path: '/monthly', redirect: '/analysis?tab=monthly' },
  { path: '/category', redirect: '/analysis?tab=category' },
  { path: '/time', redirect: '/analysis?tab=time' },
  { path: '/channels', redirect: '/analysis?tab=channels' },
  { path: '/networth', name: 'networth', component: () => import('@/views/NetWorth.vue') },
  { path: '/insights', name: 'insights', component: () => import('@/views/Insights.vue') },
  { path: '/annual', name: 'annual', component: () => import('@/views/Annual.vue') },
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
