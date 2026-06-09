<template>
  <div class="transactions-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1 class="page-title">{{ pageTitle }}</h1>
    </div>

    <!-- 卡片容器 -->
    <div class="card">
      <!-- 表格头部和筛选器 -->
      <div class="table-header">
        <h3>{{ tableTitle }}</h3>
        <div class="table-filters">
          <input v-model="filters.startDate" type="date" class="filter-date" title="起始日期" @change="onFilterChange" />
          <span class="filter-sep">~</span>
          <input v-model="filters.endDate" type="date" class="filter-date" title="结束日期" @change="onFilterChange" />
          <select v-model="filters.member" @change="onFilterChange" class="filter-select" title="成员">
            <option value="">全部成员</option>
            <option v-for="m in memberList" :key="m.id" :value="m.name">{{ m.name }}</option>
          </select>
          <select v-model="filters.source" @change="onFilterChange" class="filter-select">
            <option value="">全部来源</option>
            <option value="支付宝">支付宝</option>
            <option value="微信">微信</option>
            <option value="银行">银行</option>
          </select>
          <select v-model="filters.channel" @change="onFilterChange" class="filter-select filter-channel" title="资金渠道">
            <option value="">全部渠道</option>
            <option v-for="opt in channelOptions" :key="opt.label" :value="opt.label">
              {{ opt.label }} ({{ opt.count }})
            </option>
          </select>
          <select v-model="filters.category" @change="onFilterChange" class="filter-select">
            <option value="">全部分类</option>
            <option v-for="cat in categories" :key="cat" :value="cat">
              {{ cat }}
            </option>
          </select>
          <select v-model="filters.type" @change="onFilterChange" class="filter-select">
            <option value="">全部类型</option>
            <option v-if="!isTransfer" value="收入">收入</option>
            <option v-if="!isTransfer" value="支出">支出</option>
            <option value="转入">转账-收入</option>
            <option value="转出">转账-支出</option>
          </select>
          <input v-model.number="filters.minAmount" type="number" min="0" placeholder="金额≥" class="filter-amount" @change="onFilterChange" />
          <input v-model.number="filters.maxAmount" type="number" min="0" placeholder="金额≤" class="filter-amount" @change="onFilterChange" />
          <input
            v-model="filters.search"
            type="text"
            placeholder="搜索关键字..."
            class="filter-input"
            @keyup.enter="onFilterChange"
          />
          <button class="filter-reset" @click="resetFilters">重置</button>
        </div>
      </div>

      <!-- 表格容器 -->
      <div class="table-container">
        <div v-if="uiStore.globalLoading" class="table-loading">
          <div class="loading-spinner"></div>
          <p>加载中...</p>
        </div>

        <div v-else-if="transactions.length === 0" class="empty-state">
          <i class="fas fa-receipt empty-icon"></i>
          <p>暂无交易记录</p>
        </div>

        <table v-else id="transactionTable" class="transaction-table">
          <thead>
            <tr>
              <th>交易时间</th>
              <th>商品说明</th>
              <th>交易对方</th>
              <th>分类</th>
              <th>渠道</th>
              <th>收/支</th>
              <th>金额</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="tx in transactions" :key="tx.time + tx.description" class="table-row">
              <td>{{ tx.time }}</td>
              <td :title="tx.description">{{ tx.description }}</td>
              <td :title="tx.counterparty || ''">{{ tx.counterparty || '-' }}</td>
              <td>{{ tx.category }}</td>
              <td><span v-if="tx.channel" class="channel-tag" :title="tx.channel">{{ tx.channel }}</span><span v-else>-</span></td>
              <td>{{ typeLabel(tx.type) }}</td>
              <td :class="['amount', amountClass(tx.type)]">
                {{ parseFloat(tx.amount).toFixed(2) }}
              </td>
              <td>
                <span :class="['status-tag', tx.status === '交易成功' ? 'success' : 'refund']">
                  {{ tx.status }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 底部统计 + 图表（随筛选结果变动，类似 Excel 汇总行） -->
      <div class="bottom-stats" v-show="summary.count > 0">
        <div class="filter-summary">
          <div class="sum-item">
            <span class="sum-label">笔数</span>
            <span class="sum-value">{{ summary.count }}</span>
          </div>
          <div class="sum-item" v-if="summary.income">
            <span class="sum-label">收入</span>
            <span class="sum-value income">+{{ formatMoney(summary.income) }}</span>
          </div>
          <div class="sum-item" v-if="summary.expense">
            <span class="sum-label">支出</span>
            <span class="sum-value expense">-{{ formatMoney(summary.expense) }}</span>
          </div>
          <div class="sum-item" v-if="summary.transfer_in">
            <span class="sum-label">转入</span>
            <span class="sum-value transfer-in">+{{ formatMoney(summary.transfer_in) }}</span>
          </div>
          <div class="sum-item" v-if="summary.transfer_out">
            <span class="sum-label">转出</span>
            <span class="sum-value transfer-out">-{{ formatMoney(summary.transfer_out) }}</span>
          </div>
          <div class="sum-item" v-if="summary.internal">
            <span class="sum-label">内部搬运</span>
            <span class="sum-value internal">{{ formatMoney(summary.internal) }}</span>
          </div>
          <div class="sum-item">
            <span class="sum-label">{{ isTransfer ? '净流(入-出)' : '净额(收-支)' }}</span>
            <span class="sum-value" :class="(isTransfer ? (summary.transfer_in - summary.transfer_out) : summary.net) >= 0 ? 'income' : 'expense'">{{ formatMoney(isTransfer ? (summary.transfer_in - summary.transfer_out) : summary.net) }}</span>
          </div>
        </div>
        <div class="charts-row">
          <div class="chart-box">
            <div class="chart-title">分类占比（按金额）</div>
            <div ref="pieRef" class="chart-canvas"></div>
          </div>
          <div class="chart-box">
            <div class="chart-title">月度趋势</div>
            <div ref="lineRef" class="chart-canvas"></div>
          </div>
        </div>
      </div>

      <!-- 分页 -->
      <div class="table-pagination">
        <button
          class="pagination-btn"
          :disabled="pagination.current_page <= 1"
          @click="goToPage(pagination.current_page - 1)"
        >
          上一页
        </button>
        <span id="pageInfo" class="page-info">
          第 {{ pagination.current_page }} 页 / 共 {{ pagination.total_pages }} 页 ({{ pagination.total_records }} 条记录)
        </span>
        <button
          class="pagination-btn"
          :disabled="pagination.current_page >= pagination.total_pages"
          @click="goToPage(pagination.current_page + 1)"
        >
          下一页
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import * as echarts from 'echarts'
import { useDataStore } from '@/stores/data'
import { useUiStore } from '@/stores/ui'
import { useSessionStore } from '@/stores/session'
import { useFilterStore } from '@/stores/filter'
import api from '@/api/client'
import { formatMoney } from '@/utils/format'

const dataStore = useDataStore()
const uiStore = useUiStore()
const sessionStore = useSessionStore()
const filterStore = useFilterStore()

// 视图：/transactions=交易记录(收支，排除转账) /transfers=转账记录
const route = useRoute()
const isTransfer = computed(() => route.path === '/transfers')
const pageTitle = computed(() => (isTransfer.value ? '转账记录' : '交易记录'))
const tableTitle = computed(() => (isTransfer.value ? '转账明细' : '交易明细'))

// 收/支 类型显示：转入→转账-收入，转出→转账-支出
const TYPE_LABEL = { 转入: '转账-收入', 转出: '转账-支出' }
const typeLabel = (t) => TYPE_LABEL[t] || t
const amountClass = (t) => (t === '收入' || t === '转入') ? 'income' : (t === '不计收支' ? 'neutral' : 'expense')

const transactions = ref([])
const availableMonths = ref([])
const categories = ref([])
const channelOptions = ref([])

// 图表
const pieRef = ref(null)
const lineRef = ref(null)
let pieChart = null
let lineChart = null
const chartData = reactive({ by_category: [], by_month: [] })

const pagination = reactive({
  current_page: 1,
  per_page: 20,
  total_pages: 1,
  total_records: 0
})

const filters = reactive({
  startDate: '',
  endDate: '',
  member: '',
  source: '',
  channel: '',
  category: '',
  type: '',
  minAmount: null,
  maxAmount: null,
  search: ''
})

const memberList = ref([])

const summary = reactive({ count: 0, income: 0, expense: 0, net: 0, transfer_in: 0, transfer_out: 0, internal: 0 })

// 搜索防抖定时器
let searchTimeout = null

// 加载可用月份（从 available_dates API）
async function loadAvailableMonths() {
  try {
    const data = await api.getAvailableDates()
    console.log('[Transactions] Available months response:', data)

    if (data.months && data.months.length > 0) {
      availableMonths.value = data.months
      console.log('[Transactions] Loaded months:', availableMonths.value)
    } else {
      console.warn('[Transactions] No months found')
    }
  } catch (error) {
    console.error('[Transactions] 加载月份失败:', error)
  }
}

// 加载分类
async function loadCategories() {
  try {
    const data = await api.getCategories()
    console.log('[Transactions] Categories response:', data)

    // API 客户端会移除 success 字段，直接返回 { categories: [...] }
    if (data.categories && data.categories.length > 0) {
      categories.value = data.categories
      console.log('[Transactions] Loaded categories:', categories.value)
    } else {
      console.warn('[Transactions] No categories found')
    }
  } catch (error) {
    console.error('[Transactions] 加载分类失败:', error)
  }
}

// 解析月份筛选器值
function parseMonthFilter(monthValue) {
  if (!monthValue) return { year: '', month: '' }

  const parts = monthValue.split('-')
  if (parts.length === 2) {
    return { year: parts[0], month: parts[1] }
  }
  return { year: '', month: '' }
}

// 加载交易记录
async function loadTransactions() {
  try {
    uiStore.setGlobalLoading(true)

    // 构建参数
    const params = {
      page: pagination.current_page,
      per_page: pagination.per_page,
      view: isTransfer.value ? 'transfer' : 'normal'
    }

    // 只有当值存在时才添加参数
    if (filters.startDate) params.start_date = filters.startDate
    if (filters.endDate) params.end_date = filters.endDate
    if (filters.member) params.member = filters.member
    if (filters.source) params.source = filters.source
    if (filters.channel) params.channel = filters.channel
    if (filters.category) params.category = filters.category
    if (filters.type) params.type = filters.type
    if (filters.search) params.search = filters.search

    // 全局大额/小额筛选(侧边栏)
    const filterParams = filterStore.getFilterParams()
    Object.assign(params, filterParams)
    // 显式金额范围优先于全局
    if (filters.minAmount !== null && filters.minAmount !== '') params.min_amount = filters.minAmount
    if (filters.maxAmount !== null && filters.maxAmount !== '') params.max_amount = filters.maxAmount

    const data = await api.getTransactions(params)

    transactions.value = data.transactions || []
    pagination.current_page = data.pagination?.current_page || 1
    pagination.total_pages = data.pagination?.total_pages || 1
    pagination.total_records = data.pagination?.total_records || 0
    if (data.summary) Object.assign(summary, data.summary)
    // 渠道下拉选项（仅在为空时填充，避免随筛选漂移；重置后会再填）
    if (data.channel_options && channelOptions.value.length === 0) {
      channelOptions.value = data.channel_options
    }
    if (data.chart) {
      chartData.by_category = data.chart.by_category || []
      chartData.by_month = data.chart.by_month || []
    }
    await nextTick()
    renderCharts()

    console.log('[Transactions] Loaded', transactions.value.length, 'transactions')
  } catch (error) {
    console.error('[Transactions] Error:', error)
    uiStore.showError('加载交易记录失败: ' + error.message)
  } finally {
    uiStore.setGlobalLoading(false)
  }
}

// 渲染图表（饼图：分类占比；折线：月度趋势）
function renderCharts() {
  if (pieRef.value) {
    if (!pieChart) pieChart = echarts.init(pieRef.value)
    pieChart.setOption({
      tooltip: { trigger: 'item', formatter: p => `${p.name}<br/>¥${formatMoney(p.value)} (${p.percent}%)` },
      legend: { type: 'scroll', orient: 'vertical', right: 0, top: 'middle', textStyle: { fontSize: 11 } },
      series: [{
        type: 'pie', radius: ['40%', '70%'], center: ['36%', '50%'], avoidLabelOverlap: true,
        itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 2 }, label: { show: false },
        data: chartData.by_category.map(c => ({ name: c.name, value: c.value }))
      }]
    }, true)
    pieChart.resize()
  }
  if (lineRef.value) {
    if (!lineChart) lineChart = echarts.init(lineRef.value)
    const months = chartData.by_month.map(m => m.month)
    const series = isTransfer.value
      ? [
          { name: '转出', type: 'line', smooth: true, data: chartData.by_month.map(m => m.transfer_out || 0), itemStyle: { color: '#FF9500' } },
          { name: '转入', type: 'line', smooth: true, data: chartData.by_month.map(m => m.transfer_in || 0), itemStyle: { color: '#007AFF' } }
        ]
      : [
          { name: '收入', type: 'line', smooth: true, data: chartData.by_month.map(m => m.income), itemStyle: { color: '#34C759' } },
          { name: '支出', type: 'line', smooth: true, data: chartData.by_month.map(m => m.expense), itemStyle: { color: '#FF3B30' } }
        ]
    lineChart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { top: 0, textStyle: { fontSize: 11 } },
      grid: { left: 52, right: 16, top: 30, bottom: 24 },
      xAxis: { type: 'category', data: months, axisLabel: { fontSize: 10 } },
      yAxis: { type: 'value', axisLabel: { fontSize: 10 } },
      series
    }, true)
    lineChart.resize()
  }
}

// 筛选器变化时重新加载（重置到第一页）
function onFilterChange() {
  pagination.current_page = 1
  loadTransactions()
}

// 重置所有筛选
function resetFilters() {
  filters.startDate = ''
  filters.endDate = ''
  filters.member = ''
  filters.source = ''
  filters.channel = ''
  filters.category = ''
  filters.type = ''
  filters.minAmount = null
  filters.maxAmount = null
  filters.search = ''
  onFilterChange()
}

async function loadMembers() {
  try {
    const r = await api.getMembers()
    memberList.value = r.members || []
  } catch (e) { memberList.value = [] }
}

// 跳转到指定页码
function goToPage(page) {
  if (page >= 1 && page <= pagination.total_pages) {
    pagination.current_page = page
    loadTransactions()
  }
}

// 初始化
onMounted(async () => {
  console.log('[Transactions] Component mounted')

  await loadAvailableMonths()
  await loadCategories()
  await loadMembers()
  await loadTransactions()

  console.log('[Transactions] Initial load complete')
})

// 监听全局筛选器变化
watch(() => filterStore.currentFilter, () => {
  pagination.current_page = 1
  loadTransactions()
})

// 切换 交易记录 / 转账记录 视图（同组件复用）：重置筛选并重载
watch(() => route.path, () => {
  resetFilters()
})

// 窗口缩放重绘图表
function onResize() {
  pieChart?.resize()
  lineChart?.resize()
}
window.addEventListener('resize', onResize)

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  pieChart?.dispose()
  lineChart?.dispose()
  pieChart = null
  lineChart = null
})
</script>

<style scoped>
.transactions-page {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 20px;
}

/* 页面标题 */
.page-header {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  padding: 20px;
  position: sticky;
  top: 0;
  z-index: 100;
  background-color: var(--bg-color);
  margin: -20px -20px 24px -20px;
  border-bottom: 1px solid var(--border-color);
  backdrop-filter: saturate(180%) blur(20px);
  background-color: rgba(245, 245, 247, 0.8);
}

.page-title {
  font-size: 28px;
  font-weight: 600;
  color: var(--text-color);
  margin: 0;
}

/* 卡片容器 */
.card {
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-card);
}

/* 表格头部 */
.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.table-header h3 {
  font-size: 16px;
  font-weight: 500;
  color: var(--text-color);
  margin: 0;
}

/* 筛选器 */
.table-filters {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}

.filter-date {
  padding: 7px 10px;
  border: none;
  border-radius: 8px;
  background: var(--hover-bg);
  color: var(--text-color);
  font-size: 13px;
  outline: none;
  cursor: pointer;
}
.filter-sep { color: var(--text-secondary, #999); }
.filter-reset {
  padding: 8px 14px;
  border: none;
  border-radius: 8px;
  background: var(--hover-bg);
  color: var(--text-color);
  font-size: 13px;
  cursor: pointer;
  transition: background 0.2s;
}
.filter-reset:hover { background: var(--border-color); }

/* 筛选结果统计汇总 */
.filter-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
  padding: 14px 4px 4px;
  margin-bottom: 8px;
}
.sum-item { display: flex; flex-direction: column; gap: 3px; }
.sum-label { font-size: 12px; color: var(--text-secondary, #8e8e93); }
.sum-value { font-size: 18px; font-weight: 700; color: var(--text-color); }
.sum-value.income { color: #34C759; }
.sum-value.expense { color: #FF3B30; }
.sum-value.transfer-in { color: #007AFF; }
.sum-value.transfer-out { color: #FF9500; }

.filter-select,
.filter-input {
  padding: 8px 16px;
  border: none;
  border-radius: 8px;
  background: var(--hover-bg);
  color: var(--text-color);
  font-size: 13px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  outline: none;
}

.filter-select {
  padding-right: 32px;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23666' d='M6 8.825L1.175 4 2.238 2.938 6 6.7l3.763-3.763L10.825 4z'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
  cursor: pointer;
  /* 移除原生下拉箭头 */
  -webkit-appearance: none;
  appearance: none;
}

.filter-input {
  width: 200px;
}

.filter-select:hover,
.filter-input:hover {
  background-color: var(--border-color);
}

.filter-select:focus,
.filter-input:focus {
  background-color: white;
  box-shadow: 0 0 0 2px var(--primary-color);
}

/* 表格容器 */
.table-container {
  overflow-x: auto;
  border-radius: 12px;
  background: white;
}

.transaction-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.transaction-table th,
.transaction-table td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid var(--border-color);
  white-space: nowrap;
}

.transaction-table th {
  background: var(--bg-color);
  color: var(--secondary-text);
  font-weight: normal;
  position: sticky;
  top: 0;
  z-index: 1;
}

.transaction-table tbody tr {
  transition: background-color 0.2s;
}

.transaction-table tbody tr:hover {
  background: var(--hover-bg);
}

/* 限制商品说明列宽 */
.transaction-table td:nth-child(2) {
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 限制交易对方列宽 */
.transaction-table td:nth-child(3) {
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 金额样式 */
.amount {
  font-family: -apple-system, BlinkMacSystemFont, 'SF Mono', monospace;
  text-align: right;
}

.amount.income {
  color: #34C759;
}

.amount.expense {
  color: #FF3B30;
}

.amount.neutral {
  color: #8E8E93;
}

/* 渠道标签 */
.channel-tag {
  display: inline-block;
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: bottom;
  padding: 3px 8px;
  border-radius: 6px;
  background: var(--hover-bg, #F2F2F7);
  color: var(--text-color, #1d1d1f);
  font-size: 12px;
}

/* 渠道筛选下拉限宽 */
.filter-channel {
  max-width: 180px;
}

/* 状态标签 */
.status-tag {
  display: inline-flex;
  align-items: center;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.status-tag.success {
  background: #E4FBE6;
  color: #34C759;
}

.status-tag.refund {
  background: #FFE5E5;
  color: #FF3B30;
}

/* 分页 */
.table-pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-top: 24px;
  gap: 16px;
}

.pagination-btn {
  padding: 8px 16px;
  border: none;
  border-radius: 8px;
  background: var(--hover-bg);
  color: var(--text-color);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.pagination-btn:not(:disabled):hover {
  background: var(--primary-color);
  color: white;
}

.pagination-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.page-info {
  font-size: 13px;
  color: var(--secondary-text);
}

/* 加载和空状态 */
.table-loading,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: var(--secondary-text);
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--border-color);
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.5;
}

/* 金额范围输入 */
.filter-amount {
  width: 92px;
  padding: 8px 12px;
  border: none;
  border-radius: 8px;
  background: var(--hover-bg);
  color: var(--text-color);
  font-size: 13px;
  outline: none;
}
.filter-amount:hover { background-color: var(--border-color); }

/* 底部统计 + 图表 */
.bottom-stats {
  border-top: 1px solid var(--border-color, #eee);
  margin-top: 8px;
  padding-top: 16px;
}
.bottom-stats .filter-summary {
  padding: 4px 4px 12px;
}
.sum-value.internal { color: #8E8E93; }
.charts-row {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  margin-top: 8px;
}
.chart-box {
  flex: 1 1 320px;
  min-width: 300px;
  background: var(--hover-bg, #fafafa);
  border-radius: 12px;
  padding: 14px 12px 6px;
}
.chart-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-color);
  margin-bottom: 6px;
  padding-left: 4px;
}
.chart-canvas {
  width: 100%;
  height: 250px;
}
</style>
