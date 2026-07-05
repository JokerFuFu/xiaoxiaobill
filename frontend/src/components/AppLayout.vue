<template>
  <!-- 演示模式横幅 -->
  <div v-if="sessionStore.isDemo" class="demo-banner">
    <div class="demo-content">
      <i class="fas fa-flask"></i>
      <span>您正在浏览示例数据（仅供演示功能预览）</span>
    </div>
    <button @click="exitDemoMode" class="exit-demo-btn">退出演示</button>
  </div>

  <!-- 默认密码安全提醒(全新部署 / 仍用初始口令) -->
  <div v-if="showPwNudge" class="pw-banner">
    <div class="pw-content">
      <i class="fas fa-shield-halved"></i>
      <span>你还在使用初始密码，为账号安全建议立即修改。</span>
    </div>
    <div class="pw-actions">
      <router-link to="/settings?tab=account" class="pw-go-btn" @click="dismissPwNudge">去修改</router-link>
      <button class="pw-close-btn" @click="dismissPwNudge" title="本次会话内不再提醒"><i class="fas fa-times"></i></button>
    </div>
  </div>

  <div class="app-container">
    <!-- 侧边栏 -->
    <aside class="sidebar">
      <div class="logo">
        <img src="/images/logo_128.png" alt="小遥账单助手" class="logo-icon" />
        <span>小遥账单</span>
      </div>

      <!-- 当前用户 / 登出(置顶,避免被底部浮动筛选条遮挡) -->
      <div class="user-box">
        <div class="user-info">
          <i class="fas fa-user-circle"></i>
          <span class="user-name">{{ authStore.displayName || '未登录' }}</span>
          <span v-if="authStore.isAdmin" class="user-badge">管理员</span>
        </div>
        <button class="logout-btn" @click="onLogout" title="退出登录">
          <i class="fas fa-sign-out-alt"></i>
        </button>
      </div>

      <nav class="nav-menu">
        <!-- 分组导航:每组标题可点击折叠,折叠状态记忆到 localStorage -->
        <div v-for="group in navGroups" :key="group.key" class="nav-section">
          <!-- 分组标题(带展开/收起箭头) -->
          <button
            class="nav-section-title"
            @click="toggleGroup(group.key)"
            :aria-expanded="isGroupOpen(group.key) ? 'true' : 'false'"
          >
            <span>{{ group.label }}</span>
            <i class="fas fa-chevron-down nav-section-caret" :class="{ open: isGroupOpen(group.key) }"></i>
          </button>

          <!-- 分组内的导航项 -->
          <div class="nav-section-body" v-show="isGroupOpen(group.key)">
            <template v-for="item in group.items" :key="item.path">
              <!-- 「数据分析」保留原二级菜单交互 -->
              <div v-if="item.path === '/analysis'" class="nav-group">
                <button
                  class="nav-item nav-parent"
                  :class="{ active: $route.path === '/analysis' }"
                  @click="toggleAnalysis"
                >
                  <i class="fas fa-chart-pie icon-analysis"></i>
                  <span>数据分析</span>
                  <i class="fas fa-chevron-down nav-caret" :class="{ open: analysisOpen }"></i>
                </button>
                <div class="subnav" v-show="analysisOpen || $route.path === '/analysis'">
                  <router-link
                    v-for="s in analysisTabs" :key="s.key"
                    :to="`/analysis?tab=${s.key}`"
                    class="subnav-item"
                    :class="{ active: $route.path === '/analysis' && currentTab === s.key }"
                  >{{ s.label }}</router-link>
                </div>
              </div>
              <!-- 普通导航项(admin 项按权限显示) -->
              <router-link
                v-else-if="!item.adminOnly || authStore.isAdmin"
                :to="item.path"
                class="nav-item"
                :class="{ active: $route.path === item.path }"
              >
                <i :class="item.icon"></i>
                <span>{{ item.label }}</span>
              </router-link>
            </template>
          </div>
        </div>
      </nav>
    </aside>

    <!-- 主内容区域 -->
    <main class="content">
      <router-view />
    </main>
  </div>

  <!-- 筛选菜单 (独立于侧边栏) -->
  <div class="floating-menu">
    <button
      class="filter-btn"
      :class="{ active: filterStore.currentFilter === 'all' }"
      @click="setFilter('all')"
    >
      <i class="fas fa-list-ul"></i>
      <span>全部交易</span>
    </button>
    <button
      class="filter-btn"
      :class="{ active: filterStore.currentFilter === 'large' }"
      @click="setFilter('large')"
    >
      <i class="fas fa-coins"></i>
      <span>仅大额交易</span>
    </button>
    <button
      class="filter-btn"
      :class="{ active: filterStore.currentFilter === 'small' }"
      @click="setFilter('small')"
    >
      <i class="fas fa-coffee"></i>
      <span>仅小额交易</span>
    </button>
  </div>

  <!-- Toast 组件 -->
  <Toast v-if="uiStore.toast.show" />

  <!-- Modal 组件 -->
  <Modal v-if="uiStore.modal.show" />

  <!-- 全局加载状态 -->
  <div v-if="uiStore.globalLoading" class="global-loader">
    <div class="loader-content">
      <div class="spinner"></div>
      <div class="loader-text">加载中...</div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUiStore } from '@/stores/ui'
import { useSessionStore } from '@/stores/session'
import { useFilterStore } from '@/stores/filter'
import { useAuthStore } from '@/stores/auth'
import Toast from '@/components/common/Toast.vue'
import Modal from '@/components/common/Modal.vue'

const uiStore = useUiStore()
const sessionStore = useSessionStore()
const filterStore = useFilterStore()
const authStore = useAuthStore()
const router = useRouter()
const route = useRoute()

// 「数据分析」二级菜单
const analysisTabs = [
  { key: 'yearly', label: '年度总览' },
  { key: 'monthly', label: '月度分析' },
  { key: 'category', label: '分类分析' },
  { key: 'time', label: '时间分析' },
  { key: 'channels', label: '渠道分析' },
  { key: 'recurring', label: '订阅/定期' },
  { key: 'overseas', label: '境外消费' },
  { key: 'reconcile', label: '对账中心' },
]
const analysisOpen = ref(route.path === '/analysis')
const currentTab = computed(() => route.query.tab || 'yearly')

// 左侧导航「分组折叠」结构:每组含若干导航项(保留各自 to/图标/文案)
const navGroups = [
  {
    key: 'analysis',
    label: '分析',
    items: [
      { path: '/', label: '首页', icon: 'fas fa-home icon-home' },
      { path: '/analysis', label: '数据分析', icon: 'fas fa-chart-pie icon-analysis' },
      { path: '/insights', label: '消费洞察', icon: 'fas fa-lightbulb icon-insights' },
      { path: '/annual', label: '年度账单', icon: 'fas fa-gift icon-annual' },
    ],
  },
  {
    key: 'assets',
    label: '资产账目',
    items: [
      { path: '/networth', label: '资产负债', icon: 'fas fa-scale-balanced icon-networth' },
      { path: '/transactions', label: '交易记录', icon: 'fas fa-receipt icon-transactions' },
      { path: '/transfers', label: '转账记录', icon: 'fas fa-exchange-alt icon-transfers' },
    ],
  },
  {
    key: 'tools',
    label: '工具设置',
    items: [
      { path: '/ai', label: 'AI 助手', icon: 'fas fa-robot icon-ai' },
      { path: '/settings', label: '设置', icon: 'fas fa-cog icon-settings' },
      { path: '/admin', label: '用户管理', icon: 'fas fa-users-cog icon-admin', adminOnly: true },
      { path: '/about-author', label: '关于作者', icon: 'fas fa-user-circle icon-author' },
    ],
  },
]

// 折叠状态持久化:localStorage 记忆用户手动折叠/展开
const NAV_GROUPS_KEY = 'xiaoyao_nav_groups'

// 判断某组是否含当前路由(用于默认展开含当前项的分组)
function groupHasActiveRoute(group) {
  return group.items.some((item) => item.path === route.path)
}

// 读取持久化的折叠状态:默认全部展开,仅记忆用户手动折叠的组
function loadGroupState() {
  const state = {}
  let saved = {}
  try {
    saved = JSON.parse(localStorage.getItem(NAV_GROUPS_KEY) || '{}') || {}
  } catch {
    saved = {}
  }
  for (const group of navGroups) {
    if (groupHasActiveRoute(group)) {
      // 含当前路由的组默认展开
      state[group.key] = true
    } else if (typeof saved[group.key] === 'boolean') {
      state[group.key] = saved[group.key]
    } else {
      state[group.key] = true
    }
  }
  return state
}

const groupState = ref(loadGroupState())

function isGroupOpen(key) {
  return groupState.value[key] !== false
}

// 切换分组展开/收起,并写入 localStorage
function toggleGroup(key) {
  groupState.value = { ...groupState.value, [key]: !isGroupOpen(key) }
  try {
    localStorage.setItem(NAV_GROUPS_KEY, JSON.stringify(groupState.value))
  } catch {
    // 忽略持久化失败(如隐私模式禁用 localStorage)
  }
}

// 默认密码安全提醒:仍用初始口令且本次会话未手动关闭时显示(改密后 must_change_pw 自动转 false)
const pwNudgeDismissed = ref(false)
const showPwNudge = computed(() =>
  !sessionStore.isDemo && !!authStore.user?.must_change_pw && !pwNudgeDismissed.value)
function dismissPwNudge() { pwNudgeDismissed.value = true }
function toggleAnalysis() {
  if (route.path !== '/analysis') {
    router.push('/analysis')
    analysisOpen.value = true
  } else {
    analysisOpen.value = !analysisOpen.value
  }
}

async function onLogout() {
  if (!confirm('确定退出登录吗？')) return
  await authStore.logout()
  window.location.href = '/login'
}

async function exitDemoMode() {
  if (confirm('确定要退出演示模式吗？')) {
    try {
      await sessionStore.exitDemoMode()
      uiStore.showSuccess('已退出演示模式')
      window.location.href = '/'
    } catch (error) {
      uiStore.showError('退出失败: ' + error.message)
    }
  }
}

function setFilter(filterType) {
  console.log('[AppLayout] Setting filter to:', filterType)
  filterStore.setFilter(filterType)
  console.log('[AppLayout] Filter is now:', filterStore.currentFilter)
}

onMounted(async () => {
  // 加载会话状态
  await sessionStore.loadSessionStatus()
})
</script>

<style scoped>
/* 完全复制老前端的样式 */
.app-container {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  width: var(--sidebar-width);
  background: var(--card-bg);
  border-right: 1px solid var(--border-color);
  z-index: 1000;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

/* 侧栏顶部:当前用户 + 登出 */
.user-box {
  padding: 10px 16px;
  margin: 0 8px 4px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  gap: 8px;
}
.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
  color: var(--text-color);
  font-size: 14px;
}
.user-info .user-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.user-badge {
  font-size: 11px;
  color: #fff;
  background: #007AFF;
  border-radius: 6px;
  padding: 1px 6px;
  flex-shrink: 0;
}
.logout-btn {
  background: none;
  border: none;
  color: #86868b;
  cursor: pointer;
  font-size: 16px;
  padding: 6px;
  border-radius: 8px;
}
.logout-btn:hover { color: #ff3b30; background: rgba(255, 59, 48, 0.08); }
.icon-ai { color: #AF52DE; }
.icon-admin { color: #FF9500; }

.logo {
  font-family: var(--font-family-display);
  height: var(--header-height);
  display: flex;
  align-items: center;
  padding: 0 20px;
  font-size: 20px;
  font-weight: 500;
  letter-spacing: -0.025em;
  color: var(--text-color);
}

.logo-icon {
  width: 64px;
  height: 64px;
  margin-right: 12px;
  object-fit: contain;
}

.nav-menu {
  padding: 8px 0 190px;   /* 底部留白,避免最后几项被浮动筛选条遮挡 */
  flex: 1;
}

.nav-item {
  padding: 12px 20px;
  margin: 4px 8px;
  display: flex;
  align-items: center;
  color: var(--text-color);
  text-decoration: none;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-family: var(--font-family-text);
  letter-spacing: -0.016em;
}

.nav-item:hover {
  background: var(--hover-bg);
  color: var(--primary-color);
}

.nav-item.active {
  background: var(--hover-bg);
  color: var(--primary-color);
  font-weight: 500;
}

.nav-item i {
  margin-right: 12px;
  width: 20px;
  text-align: center;
  font-size: 16px;
}

/* 为每个菜单项图标添加颜色 */
.icon-home { color: #007AFF; }
.icon-yearly { color: #5856D6; }
.icon-monthly { color: #34C759; }
.icon-category { color: #FF9500; }
.icon-time { color: #AF52DE; }
.icon-insights { color: #FFCC00; }
.icon-transactions { color: #30B0C7; }
.icon-transfers { color: #AF52DE; }
.icon-channels { color: #FF9500; }
.icon-settings { color: #8E8E93; }
.icon-author { color: #FF2D55; }
.icon-analysis { color: #5856D6; }
.icon-networth { color: #34C759; }

/* 数据分析:二级菜单 */
.nav-group { display: flex; flex-direction: column; }
.nav-parent {
  width: calc(100% - 16px);
  font-family: inherit; background: none; border: none; text-align: left; cursor: pointer;
}
.nav-parent .nav-caret {
  margin-left: auto; margin-right: 0; width: auto; font-size: 11px; color: #b0b0b8;
  transition: transform .2s;
}
.nav-parent .nav-caret.open { transform: rotate(180deg); }
.subnav { display: flex; flex-direction: column; margin: 0 8px 4px 8px; }
.subnav-item {
  display: block; padding: 9px 20px 9px 48px; margin: 1px 0; border-radius: var(--radius-sm);
  color: var(--secondary-text, #86868b); text-decoration: none; font-size: 13.5px; transition: all .2s;
}
.subnav-item:hover { background: var(--hover-bg); color: var(--primary-color); }
.subnav-item.active { background: var(--hover-bg); color: var(--primary-color); font-weight: 500; }

/* 分组导航:分组标题(可折叠)+ 分组内容 */
.nav-section {
  margin-bottom: var(--space-xs);
}
.nav-section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: calc(100% - 2 * var(--space-sm));
  margin: var(--space-sm) var(--space-sm) var(--space-xs);
  padding: var(--space-xs) var(--space-md);
  background: none;
  border: none;
  cursor: pointer;
  color: var(--secondary-text);
  font-size: var(--fs-xs);
  font-weight: 600;
  letter-spacing: 0.04em;
  transition: color var(--transition-fast);
}
.nav-section-title:hover { color: var(--text-color); }
.nav-section-title:focus-visible {
  outline: none;
  box-shadow: var(--focus-ring);
  border-radius: var(--radius-sm);
}
.nav-section-caret {
  font-size: 10px;
  transition: transform var(--transition-base);
}
.nav-section-caret.open { transform: rotate(180deg); }
.nav-section-body {
  display: flex;
  flex-direction: column;
}

.content {
  flex: 1;
  margin-left: var(--sidebar-width);
  padding: 20px;
  background: var(--bg-color);
  min-height: 100vh;
}

/* 演示模式横幅 */
.demo-banner {
  background: #FFF8E1;
  color: #F57F17;
  padding: 10px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #FFE0B2;
  position: sticky;
  top: 0;
  z-index: 1001;
}

.demo-content {
  display: flex;
  align-items: center;
  gap: 8px;
}

.demo-content i {
  font-size: 16px;
}

.exit-demo-btn {
  background: #F57F17;
  color: white;
  border: none;
  padding: 6px 16px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.exit-demo-btn:hover {
  background: #E65100;
}

/* 默认密码安全提醒横幅 */
.pw-banner {
  background: #FFF1F0;
  color: #C0392B;
  padding: 10px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #FBD5D0;
  position: sticky;
  top: 0;
  z-index: 1001;
}
.pw-content { display: flex; align-items: center; gap: 8px; font-size: 14px; }
.pw-content i { font-size: 16px; }
.pw-actions { display: flex; align-items: center; gap: 8px; }
.pw-go-btn {
  background: #C0392B; color: #fff; border: none;
  padding: 6px 16px; border-radius: var(--radius-sm);
  font-size: 13px; cursor: pointer; text-decoration: none; transition: background 0.2s ease;
}
.pw-go-btn:hover { background: #A93226; }
.pw-close-btn {
  background: transparent; border: none; color: #C0392B;
  cursor: pointer; font-size: 15px; padding: 4px 6px; line-height: 1;
}
.pw-close-btn:hover { color: #A93226; }

/* 全局加载状态 */
.global-loader {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.loader-content {
  text-align: center;
}

.spinner {
  width: 48px;
  height: 48px;
  border: 4px solid rgba(255, 255, 255, 0.2);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 16px;
}

.loader-text {
  color: white;
  font-size: 14px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* 浮动筛选菜单 */
.floating-menu {
  position: fixed;
  left: 0;
  bottom: 24px;
  width: var(--sidebar-width);
  padding: 0 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  z-index: 1200;
}

.filter-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  border: none;
  border-radius: var(--radius-md);
  background: var(--card-bg);
  color: var(--text-color);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
  width: 100%;
  box-shadow: var(--shadow-float);
}

.filter-btn:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-hover);
}

.filter-btn.active {
  background: var(--primary-color);
  color: white;
}

.filter-btn i {
  font-size: 16px;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .content {
    margin-left: 0;
    padding: 16px;
  }

  .sidebar {
    width: 60px;
    transform: translateX(-100%);
    transition: transform 0.3s ease;
  }

  .sidebar:hover,
  .sidebar.active {
    transform: translateX(0);
    width: 240px;
  }

  .nav-item span {
    display: none;
  }

  .sidebar:hover .nav-item span,
  .sidebar.active .nav-item span {
    display: inline;
  }

  .logo span {
    display: none;
  }

  .sidebar:hover .logo span,
  .sidebar.active .logo span {
    display: inline;
  }

  .demo-banner {
    flex-direction: column;
    gap: 8px;
    text-align: center;
  }

  /* 折叠态:分组标题(纯文本)整体隐藏,hover 展开侧栏时再显示 */
  .nav-section-title {
    display: none;
  }

  .sidebar:hover .nav-section-title,
  .sidebar.active .nav-section-title {
    display: flex;
  }

  /* 移动端隐藏筛选按钮文本 */
  .filter-btn span {
    display: none;
  }

  .sidebar:hover .filter-btn span,
  .sidebar.active .filter-btn span {
    display: inline;
  }

  .filter-btn {
    justify-content: center;
  }
}
</style>
