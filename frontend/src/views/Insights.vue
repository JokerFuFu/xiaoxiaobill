<template>
  <div class="insights-page">
    <div class="page-header">
      <h1 class="page-title">消费洞察</h1>
      <div class="control-group">
        <button @click="prevYear" class="control-button" :disabled="!canGoPrev">
          <i class="fas fa-chevron-left"></i>
        </button>
        <span class="control-display">{{ currentYear }}年</span>
        <button @click="nextYear" class="control-button" :disabled="!canGoNext">
          <i class="fas fa-chevron-right"></i>
        </button>
      </div>
    </div>

    <div v-if="uiStore.globalLoading && !insightsData" class="page-loading">
      <div class="loading-spinner"></div>
      <p>加载中...</p>
    </div>

    <div v-else-if="insightsData" class="insights-content">
      <!-- 顶部区域：桑基图 + 年度故事 -->
      <div class="top-analysis-section">
        <!-- 桑基图 -->
        <SankeyChart :sankey-data="insightsData.sankey_data" />

        <!-- 年度故事 -->
        <StoryMode :story-data="storyData" />
      </div>

      <!-- 核心分析网格 -->
      <div class="core-analysis-grid">
        <!-- 消费画像 -->
        <ConsumerProfile :tags="insightsData.tags" />

        <!-- 最常光顾 -->
        <FrequentMerchants :merchants="frequentMerchants" />

        <!-- 消费场景 -->
        <ConsumerScenario
          :scenario-analysis="insightsData.scenario_analysis"
          :payment-analysis="insightsData.payment_analysis"
        />

        <!-- 银行卡维度 -->
        <BankCardDimension :bank-card-analysis="insightsData.bank_card_analysis" />

        <!-- 消费习惯 -->
        <ConsumerHabit
          :habit-analysis="insightsData.habit_analysis"
          :nighttime-analysis="insightsData.nighttime_analysis"
          :engel-coefficient="insightsData.engel_coefficient"
        />
      </div>

      <!-- 高级洞察网格 -->
      <AdvancedInsights
        :latte-factor="insightsData.latte_factor"
        :subscription-analysis="insightsData.subscription_analysis"
        :inflation-analysis="insightsData.inflation_analysis"
        :brand-loyalty="insightsData.brand_loyalty"
        :weekend-monday="insightsData.weekend_monday"
      />

      <!-- 高级可视化图表区域 -->
      <div class="advanced-viz-section">
        <h2 class="section-title">深度洞察</h2>

        <!-- 时间密码：河流图 + 热力图 + 雷达图 -->
        <TimeInsightCharts
          :themeriver-data="insightsData.themeriver_data"
          :heatmap-data="insightsData.heatmap_data"
          :radar-data="insightsData.radar_data"
        />

        <!-- 决策心理：象限图 + 和弦图 + 漏斗图 -->
        <DecisionInsightCharts
          :quadrant-data="insightsData.quadrant_data"
          :chord-data="insightsData.chord_data"
          :funnel-data="insightsData.funnel_data"
        />

        <!-- 结构解析：帕累托图 + 词云图 + 箱形图 -->
        <StructureInsightCharts
          :pareto-data="insightsData.pareto_data"
          :wordcloud-data="insightsData.wordcloud_data"
          :boxplot-data="insightsData.boxplot_data"
        />
      </div>
    </div>

    <div v-else class="empty-state">
      <i class="fas fa-chart-bar empty-icon"></i>
      <p>暂无数据</p>
      <button class="btn btn-primary" @click="$router.push('/settings')">
        上传账单
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { useDataStore } from '@/stores/data'
import { useUiStore } from '@/stores/ui'
import { useSessionStore } from '@/stores/session'
import { useFilterStore } from '@/stores/filter'
import api from '@/api/client'

// 各展示区块子组件
import SankeyChart from '@/components/insights/SankeyChart.vue'
import StoryMode from '@/components/insights/StoryMode.vue'
import ConsumerProfile from '@/components/insights/ConsumerProfile.vue'
import FrequentMerchants from '@/components/insights/FrequentMerchants.vue'
import ConsumerScenario from '@/components/insights/ConsumerScenario.vue'
import BankCardDimension from '@/components/insights/BankCardDimension.vue'
import ConsumerHabit from '@/components/insights/ConsumerHabit.vue'
import AdvancedInsights from '@/components/insights/AdvancedInsights.vue'
import TimeInsightCharts from '@/components/insights/TimeInsightCharts.vue'
import DecisionInsightCharts from '@/components/insights/DecisionInsightCharts.vue'
import StructureInsightCharts from '@/components/insights/StructureInsightCharts.vue'

const dataStore = useDataStore()
const uiStore = useUiStore()
const sessionStore = useSessionStore()
const filterStore = useFilterStore()

// 状态
const currentYear = ref(new Date().getFullYear())
const availableYears = ref([])
const insightsData = ref(null)

// 计算属性
const canGoPrev = computed(() => {
  const currentIndex = availableYears.value.indexOf(currentYear.value)
  return currentIndex < availableYears.value.length - 1
})

const canGoNext = computed(() => {
  const currentIndex = availableYears.value.indexOf(currentYear.value)
  return currentIndex > 0
})

// 年度故事数据
const storyData = computed(() => {
  return insightsData.value?.story_data || []
})

// 常去商家列表
const frequentMerchants = computed(() => {
  return insightsData.value?.merchant_analysis?.frequent_merchants || []
})

// 方法
function prevYear() {
  const currentIndex = availableYears.value.indexOf(currentYear.value)
  if (currentIndex < availableYears.value.length - 1) {
    currentYear.value = availableYears.value[currentIndex + 1]
    loadData(currentYear.value)
  }
}

function nextYear() {
  const currentIndex = availableYears.value.indexOf(currentYear.value)
  if (currentIndex > 0) {
    currentYear.value = availableYears.value[currentIndex - 1]
    loadData(currentYear.value)
  }
}

async function loadData(year) {
  try {
    console.log('[Insights] Loading data for year:', year, 'filter:', filterStore.currentFilter)
    uiStore.setGlobalLoading(true)

    const params = {
      year: year,
      ...filterStore.getFilterParams()
    }

    const data = await api.getAnalysis(params)
    console.log('[Insights] Data loaded:', data)

    insightsData.value = data

    // 保持原有时机：数据就绪后等待 DOM 更新，子组件在挂载/props 变化时自行渲染
    await nextTick()
  } catch (error) {
    console.error('[Insights] Failed to load data:', error)
    uiStore.showError('加载数据失败: ' + error.message)
  } finally {
    uiStore.setGlobalLoading(false)
  }
}

// 监听筛选器变化
watch(() => filterStore.currentFilter, () => {
  if (currentYear.value) {
    loadData(currentYear.value)
  }
})

onMounted(async () => {
  try {
    uiStore.setGlobalLoading(true)

    await dataStore.loadAvailableYears()
    availableYears.value = dataStore.availableYears.sort((a, b) => b - a)

    if (availableYears.value.length > 0) {
      currentYear.value = availableYears.value[0]

      if (sessionStore.isDemo) {
        await new Promise(resolve => setTimeout(resolve, 500))
      }

      await loadData(currentYear.value)
    }
  } catch (error) {
    console.error('Insights page init error:', error)
    uiStore.showError('页面初始化失败: ' + error.message)
  } finally {
    uiStore.setGlobalLoading(false)
  }
})
</script>

<style scoped>
.insights-page {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 20px;
}

.page-header {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  padding: 0 20px;
  margin-bottom: 24px;
}

.page-title {
  font-size: 28px;
  font-weight: 600;
  color: var(--text-color);
  margin: 0;
}

.control-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.control-button {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--text-color);
  transition: all 0.2s ease;
}

.control-button:hover:not(:disabled) {
  background: var(--hover-bg);
  border-color: var(--primary-color);
}

.control-button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.control-display {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-color);
  min-width: 80px;
  text-align: center;
}

/* 顶部区域 */
.top-analysis-section {
  display: flex;
  gap: 24px;
  margin-bottom: 24px;
  height: 500px;
}

/* 核心分析网格 */
.core-analysis-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin-bottom: 20px;
}

/* 高级可视化区域 */
.advanced-viz-section {
  margin-bottom: 20px;
}

.section-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-color);
  margin: 0 0 20px 0;
}

/* 加载和空状态 */
.page-loading,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  color: var(--secondary-text);
}

.loading-spinner {
  width: 48px;
  height: 48px;
  border: 4px solid var(--border-color);
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 20px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 20px;
  opacity: 0.5;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  border: none;
  border-radius: var(--radius-md);
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-primary {
  background: var(--primary-color);
  color: white;
}

.btn-primary:hover {
  background: #0066E6;
}

@media (max-width: 1200px) {
  .top-analysis-section {
    flex-direction: column;
    height: auto;
  }

  .core-analysis-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .page-header {
    grid-template-columns: 1fr;
    gap: 16px;
    text-align: center;
  }
}
</style>
