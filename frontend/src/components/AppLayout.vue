<template>
  <!-- 演示模式横幅 -->
  <div v-if="sessionStore.isDemo" class="demo-banner">
    <div class="demo-content">
      <i class="fas fa-flask"></i>
      <span>您正在浏览示例数据（仅供演示功能预览）</span>
    </div>
    <button @click="exitDemoMode" class="exit-demo-btn">退出演示</button>
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
        <router-link to="/" class="nav-item" :class="{ active: $route.path === '/' }">
          <i class="fas fa-home icon-home"></i>
          <span>首页</span>
        </router-link>
        <!-- 数据分析(二级菜单) -->
        <div class="nav-group">
          <button class="nav-item nav-parent" :class="{ active: $route.path === '/analysis' }" @click="toggleAnalysis">
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
        <router-link to="/networth" class="nav-item" :class="{ active: $route.path === '/networth' }">
          <i class="fas fa-scale-balanced icon-networth"></i>
          <span>资产负债</span>
        </router-link>
        <router-link to="/insights" class="nav-item" :class="{ active: $route.path === '/insights' }">
          <i class="fas fa-lightbulb icon-insights"></i>
          <span>消费洞察</span>
        </router-link>
        <router-link to="/transactions" class="nav-item" :class="{ active: $route.path === '/transactions' }">
          <i class="fas fa-receipt icon-transactions"></i>
          <span>交易记录</span>
        </router-link>
        <router-link to="/transfers" class="nav-item" :class="{ active: $route.path === '/transfers' }">
          <i class="fas fa-exchange-alt icon-transfers"></i>
          <span>转账记录</span>
        </router-link>
        <router-link to="/ai" class="nav-item" :class="{ active: $route.path === '/ai' }">
          <i class="fas fa-robot icon-ai"></i>
          <span>AI 助手</span>
        </router-link>
        <router-link to="/settings" class="nav-item" :class="{ active: $route.path === '/settings' }">
          <i class="fas fa-cog icon-settings"></i>
          <span>设置</span>
        </router-link>
        <router-link v-if="authStore.isAdmin" to="/admin" class="nav-item" :class="{ active: $route.path === '/admin' }">
          <i class="fas fa-users-cog icon-admin"></i>
          <span>用户管理</span>
        </router-link>
        <router-link to="/about-author" class="nav-item" :class="{ active: $route.path === '/about-author' }">
          <i class="fas fa-user-circle icon-author"></i>
          <span>关于作者</span>
        </router-link>
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
  { key: 'income', label: '收入分析' },
  { key: 'category', label: '分类分析' },
  { key: 'time', label: '时间分析' },
  { key: 'channels', label: '渠道分析' },
  { key: 'reconcile', label: '对账中心' },
]
const analysisOpen = ref(route.path === '/analysis')
const currentTab = computed(() => route.query.tab || 'yearly')
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
