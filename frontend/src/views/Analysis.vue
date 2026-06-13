<template>
  <div class="analysis-wrap">
    <!-- 二级标签 -->
    <div class="analysis-tabs">
      <button
        v-for="t in tabs" :key="t.key"
        class="atab" :class="{ active: active === t.key }"
        @click="active = t.key"
      >
        <i :class="t.icon"></i> <span>{{ t.label }}</span>
      </button>
    </div>

    <!-- 顶部 AI 智能分析(随标签切换维度;订阅/境外暂无 AI 维度则不渲染) -->
    <AiAnalysisPanel v-if="scope" :scope="scope" :key="scope" />

    <!-- 子分析(保活,切换不丢图表与状态) -->
    <keep-alive>
      <component :is="current" />
    </keep-alive>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AiAnalysisPanel from '@/components/AiAnalysisPanel.vue'
import Yearly from './Yearly.vue'
import Monthly from './Monthly.vue'
import Category from './Category.vue'
import Time from './Time.vue'
import Channels from './Channels.vue'
import Reconcile from './Reconcile.vue'
import Recurring from './Recurring.vue'
import Overseas from './Overseas.vue'

const tabs = [
  { key: 'yearly', label: '年度总览', icon: 'fas fa-calendar-alt', comp: Yearly, scope: 'yearly' },
  { key: 'monthly', label: '月度分析', icon: 'fas fa-chart-line', comp: Monthly, scope: 'monthly' },
  { key: 'category', label: '分类分析', icon: 'fas fa-tags', comp: Category, scope: 'category' },
  { key: 'time', label: '时间分析', icon: 'fas fa-clock', comp: Time, scope: 'time' },
  { key: 'channels', label: '渠道分析', icon: 'fas fa-credit-card', comp: Channels, scope: 'channel' },
  { key: 'recurring', label: '订阅/定期', icon: 'fas fa-repeat', comp: Recurring, scope: null },
  { key: 'overseas', label: '境外消费', icon: 'fas fa-earth-asia', comp: Overseas, scope: null },
  { key: 'reconcile', label: '对账中心', icon: 'fas fa-scale-balanced', comp: Reconcile, scope: 'reconcile' },
]
const validKeys = tabs.map(t => t.key)

const route = useRoute()
const router = useRouter()

const initial = validKeys.includes(route.query.tab) ? route.query.tab : 'yearly'
const active = ref(initial)

const currentTab = computed(() => tabs.find(t => t.key === active.value) || tabs[0])
const current = computed(() => currentTab.value.comp)
const scope = computed(() => currentTab.value.scope)

// 标签 ↔ URL query 同步(刷新/侧栏二级菜单跳转都能定位)
watch(active, (v) => {
  if (route.query.tab !== v) router.replace({ path: '/analysis', query: { ...route.query, tab: v } })
})
watch(() => route.query.tab, (v) => {
  if (v && validKeys.includes(v) && v !== active.value) active.value = v
})
</script>

<style scoped>
.analysis-wrap { max-width: 1400px; margin: 0 auto; }
.analysis-tabs {
  display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 18px;
  background: var(--card-bg, #fff); border: 1px solid var(--border-color, #ecedf1); border-radius: 14px; padding: 6px;
  position: sticky; top: 0; z-index: 20;
}
.atab {
  display: inline-flex; align-items: center; gap: 7px; height: 40px; padding: 0 18px;
  border: none; background: none; color: #5a5a60; font-size: 14px; font-weight: 500; border-radius: 10px;
  cursor: pointer; transition: all .15s;
}
.atab i { font-size: 14px; opacity: .85; }
.atab:hover { background: #f3f5f9; color: #007AFF; }
.atab.active { background: #007AFF; color: #fff; box-shadow: 0 4px 12px rgba(0,122,255,.2); }
@media (max-width: 768px) {
  .atab span { display: none; }
  .atab { padding: 0 14px; }
}
</style>
