import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api/client'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)          // {id, username, display_name, role, is_admin}
  const isDemo = ref(false)
  const checked = ref(false)      // 是否已向后端确认过登录态

  const isAuthenticated = computed(() => !!user.value || isDemo.value)
  const isAdmin = computed(() => !!user.value && user.value.is_admin)
  const displayName = computed(() => isDemo.value ? '演示账号' : (user.value?.display_name || user.value?.username || ''))

  async function ensureLoaded() {
    if (checked.value) return
    await refresh()
  }

  async function refresh() {
    try {
      const r = await api.authMe()
      if (r.authenticated) {
        isDemo.value = !!r.is_demo
        user.value = r.is_demo ? null : r.user
      } else {
        user.value = null
        isDemo.value = false
      }
    } catch (e) {
      user.value = null
      isDemo.value = false
    } finally {
      checked.value = true
    }
  }

  async function login(username, password) {
    const r = await api.login(username, password)
    user.value = r.user
    isDemo.value = false
    checked.value = true
    return r
  }

  async function logout() {
    try { await api.logout() } catch (e) { /* ignore */ }
    user.value = null
    isDemo.value = false
    checked.value = true
    localStorage.removeItem('xiaoyao_demo_mode')
  }

  return { user, isDemo, checked, isAuthenticated, isAdmin, displayName, ensureLoaded, refresh, login, logout }
})
