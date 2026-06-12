<template>
  <div class="income-page">
    <!-- 页头 -->
    <div class="page-header">
      <div>
        <h1 class="page-title">收入分析</h1>
        <p class="page-sub">工资、理财收益与其他收入 —— 基于资金性质口径，与对账中心同源。</p>
      </div>
      <div class="year-side">
        <div class="year-filter">
          <button
            v-for="y in years"
            :key="y"
            class="year-btn"
            :class="{ active: year === y }"
            @click="setYear(y)"
          >{{ y }}</button>
        </div>
        <p class="year-note">年份影响 KPI / 理财 / 其他收入；薪资趋势始终为全历史。</p>
      </div>
    </div>

    <!-- AI 智能分析(收入顾问视角) -->
    <AiAnalysisPanel scope="income" />

    <div v-if="loading" class="state-box">数据加载中…</div>
    <div v-else-if="error" class="state-box error">{{ error }}</div>
    <div v-else-if="!data || data.empty" class="state-box">暂无账单数据，请先在「设置」上传账单，再来看收入分析。</div>

    <template v-else>
      <!-- KPI -->
      <div class="kpi-row">
        <div class="kpi-card">
          <div class="kpi-icon" style="background:#34C75922;color:#34C759"><i class="fas fa-sack-dollar"></i></div>
          <div>
            <div class="kpi-num kpi-strong" style="color:#34C759">¥{{ fmt(overview.real_income) }}</div>
            <div class="kpi-label">本年真实收入</div>
          </div>
        </div>
        <div class="kpi-card">
          <div class="kpi-icon" style="background:#34C75922;color:#34C759"><i class="fas fa-briefcase"></i></div>
          <div>
            <div class="kpi-num">¥{{ fmt(bucketAmt('工资收入')) }}</div>
            <div class="kpi-label">本年工资</div>
          </div>
        </div>
        <div class="kpi-card">
          <div class="kpi-icon" style="background:#007AFF22;color:#007AFF"><i class="fas fa-calendar-check"></i></div>
          <div>
            <div class="kpi-num">¥{{ fmt(stats.avg_recent12) }}</div>
            <div class="kpi-label">平均月薪 · 近12月</div>
          </div>
        </div>
        <div class="kpi-card">
          <div class="kpi-icon" style="background:#5856D622;color:#5856D6"><i class="fas fa-chart-line"></i></div>
          <div>
            <div class="kpi-num">¥{{ fmt(invest.total) }}</div>
            <div class="kpi-label">本年理财收益</div>
          </div>
        </div>
        <div class="kpi-card">
          <div class="kpi-icon" style="background:#FF950022;color:#FF9500"><i class="fas fa-coins"></i></div>
          <div>
            <div class="kpi-num">¥{{ fmt(bucketAmt('其他收入')) }}</div>
            <div class="kpi-label">本年其他收入</div>
          </div>
        </div>
      </div>

      <!-- 薪资分析（核心） -->
      <div class="section">
        <h2 class="section-title">
          <i class="fas fa-money-check-dollar"></i> 薪资分析
          <span class="title-tag">全历史 · 不随年份切换</span>
        </h2>

        <div v-if="!salaryMonths.length" class="chart-card">
          <div class="empty-hint">暂无工资数据。若工资入账未被识别，可在「对账中心 · 口径规则」添加一条把发薪流水标为「工资收入」的规则。</div>
        </div>

        <template v-else>
          <!-- a. 月度薪资 -->
          <div class="chart-card">
            <h3 class="chart-title">月度薪资（<span class="dot" style="background:#34C759"></span>普通月 / <span class="dot" style="background:#FF9500"></span>奖金月，虚线为中位数）</h3>
            <div ref="salaryRef" class="chart chart-lg"></div>
          </div>

          <!-- b. 指标条 -->
          <div class="stat-strip">
            <div class="stat-cell">
              <div class="stat-num">¥{{ fmt(stats.total) }}</div>
              <div class="stat-label">累计工资</div>
            </div>
            <div class="stat-cell">
              <div class="stat-num">¥{{ fmt(stats.median) }}</div>
              <div class="stat-label">月薪中位数</div>
            </div>
            <div class="stat-cell">
              <div class="stat-num">¥{{ fmt(stats.max_amount) }}</div>
              <div class="stat-label">最高月 {{ stats.max_month || '—' }}</div>
            </div>
            <div class="stat-cell">
              <div class="stat-num">{{ stats.typical_payday != null ? `每月 ${stats.typical_payday} 号` : '—' }}</div>
              <div class="stat-label">典型发薪日</div>
            </div>
            <div class="stat-cell">
              <div class="stat-num" :style="yoyStyle">{{ yoyText }}</div>
              <div class="stat-label">月均同比</div>
            </div>
            <div class="stat-cell">
              <div class="stat-num">{{ pct(stats.avg_saving_rate) }}</div>
              <div class="stat-label">平均结余率</div>
            </div>
          </div>

          <!-- 缺发薪记录提示 -->
          <div v-if="(stats.missing_months || []).length" class="warn-banner">
            <i class="fas fa-triangle-exclamation"></i>
            以下月份缺发薪记录：{{ stats.missing_months.join('、') }}（可能账单未导入）
          </div>

          <!-- c. 工资 vs 消费 -->
          <div class="chart-card">
            <h3 class="chart-title">工资 vs 消费（储蓄能力 · 近 12 个月，折线为结余率）</h3>
            <div ref="savingRef" class="chart"></div>
          </div>

          <!-- d. 口径审计 -->
          <div class="feed-card">
            <div class="audit-head">
              <span class="audit-title"><i class="fas fa-magnifying-glass-dollar"></i> 口径审计</span>
              <span v-if="audit.salary_channel" class="channel-badge"><i class="fas fa-building-columns"></i> 锚定工资卡：{{ audit.salary_channel }}</span>
            </div>

            <div v-if="auditClean" class="ok-line">
              <i class="fas fa-circle-check"></i> 工资口径干净：全部工资行都在 {{ audit.salary_channel || '工资卡' }}，无疑似漏标 ✓
            </div>

            <template v-else>
              <div v-if="(audit.off_channel || []).length" class="audit-block">
                <h4 class="audit-sub">标为工资但不在工资卡</h4>
                <table class="mini-table">
                  <thead>
                    <tr><th>时间</th><th class="num">金额</th><th>渠道</th><th>说明</th></tr>
                  </thead>
                  <tbody>
                    <tr v-for="(r, i) in audit.off_channel" :key="'oc' + i">
                      <td>{{ r.time }}</td>
                      <td class="num">¥{{ fmt(r.amount) }}</td>
                      <td>{{ r.channel || '—' }}</td>
                      <td class="ellipsis">{{ r.desc || '—' }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div v-if="(audit.missed || []).length" class="audit-block">
                <h4 class="audit-sub">工资卡大额入账未标工资（疑似奖金 / 报销漏标）</h4>
                <table class="mini-table">
                  <thead>
                    <tr><th>时间</th><th class="num">金额</th><th>资金性质</th><th>对方</th><th>说明</th></tr>
                  </thead>
                  <tbody>
                    <tr v-for="(r, i) in audit.missed" :key="'ms' + i">
                      <td>{{ r.time }}</td>
                      <td class="num">¥{{ fmt(r.amount) }}</td>
                      <td>{{ r.nature || '—' }}</td>
                      <td class="ellipsis">{{ r.counterparty || '—' }}</td>
                      <td class="ellipsis">{{ r.desc || '—' }}</td>
                    </tr>
                  </tbody>
                </table>
                <p class="card-note">确认是工资后，可在「对账中心 · 口径规则」加一条口径规则将其归入工资收入。</p>
              </div>
            </template>
          </div>
        </template>
      </div>

      <!-- 理财收益 -->
      <div class="section">
        <h2 class="section-title"><i class="fas fa-chart-line"></i> 理财收益</h2>
        <div class="two-col">
          <div class="chart-card">
            <h3 class="chart-title">月度已实现收益与累计</h3>
            <div v-if="!investMonths.length" class="empty-hint">本期无已实现收益。</div>
            <div v-else ref="investRef" class="chart"></div>
          </div>
          <div class="feed-card">
            <div class="invest-total">
              <div class="kpi-num" style="color:#5856D6">¥{{ fmt(invest.total) }}</div>
              <div class="kpi-label">总收益（{{ invest.count || 0 }} 笔）</div>
            </div>
            <table v-if="(invest.by_channel || []).length" class="mini-table">
              <thead>
                <tr><th>渠道</th><th class="num">收益</th><th class="num">笔数</th></tr>
              </thead>
              <tbody>
                <tr v-for="c in invest.by_channel" :key="c.channel">
                  <td class="strong">{{ c.channel }}</td>
                  <td class="num">¥{{ fmt(c.amount) }}</td>
                  <td class="num">{{ c.count }}</td>
                </tr>
              </tbody>
            </table>
            <div class="principal-box">
              <div class="principal-row"><span>申购</span><b>¥{{ fmt(principal.subscribe) }}</b></div>
              <div class="principal-row"><span>赎回</span><b>¥{{ fmt(principal.redeem) }}</b></div>
              <div class="principal-row"><span>在外净投入</span><b style="color:#5856D6">¥{{ fmt(principal.net_out) }}</b></div>
            </div>
            <p v-if="invest.note" class="card-note">{{ invest.note }}</p>
          </div>
        </div>
      </div>

      <!-- 其他收入 -->
      <div class="section">
        <h2 class="section-title"><i class="fas fa-coins"></i> 其他收入</h2>
        <div v-if="!(other.groups || []).length" class="feed-card">
          <div class="empty-hint">本期无其他收入。</div>
        </div>
        <template v-else>
          <div class="group-grid">
            <div v-for="g in other.groups" :key="g.group" class="group-card">
              <div class="group-head">
                <span class="group-name">{{ g.group }}</span>
                <span class="group-meta">¥{{ fmt(g.amount) }} · {{ g.count }} 笔</span>
              </div>
              <ul class="top-list">
                <li v-for="(t, i) in (g.top || []).slice(0, 3)" :key="i">
                  <span class="top-desc">{{ t.desc || '—' }}</span>
                  <span class="top-amt">¥{{ fmt(t.amount) }}</span>
                  <span class="top-time">{{ t.time }}</span>
                </li>
              </ul>
            </div>
          </div>
          <div v-if="(other.months || []).length" class="chart-card">
            <h3 class="chart-title">其他收入月度趋势</h3>
            <div ref="otherRef" class="chart chart-sm"></div>
          </div>
        </template>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, onActivated, nextTick } from 'vue'
import * as echarts from 'echarts'
import api from '@/api/client'
import { useUiStore } from '@/stores/ui'
import AiAnalysisPanel from '@/components/AiAnalysisPanel.vue'

defineOptions({ name: 'Income' })

const ui = useUiStore()

const loading = ref(true)
const error = ref('')
const data = ref(null)
const year = ref(null)
const years = ref([])

const salaryRef = ref(null)
const savingRef = ref(null)
const investRef = ref(null)
const otherRef = ref(null)
let salaryChart = null, savingChart = null, investChart = null, otherChart = null

const fmt = (v) => (v == null ? '—' : Number(v).toLocaleString('zh-CN', { maximumFractionDigits: 2 }))
const fmtWan = (v) => {
  const n = Number(v || 0)
  return Math.abs(n) >= 10000 ? (n / 10000).toFixed(2) + '万' : fmt(n)
}
const pct = (v) => (v == null ? '—' : fmt(v) + '%')

const overview = computed(() => (data.value && data.value.overview) || {})
const stats = computed(() => (data.value && data.value.salary && data.value.salary.stats) || {})
const audit = computed(() => (data.value && data.value.salary && data.value.salary.audit) || {})
const salaryMonths = computed(() => (data.value && data.value.salary && data.value.salary.months) || [])
const invest = computed(() => (data.value && data.value.invest) || {})
const investMonths = computed(() => invest.value.months || [])
const principal = computed(() => invest.value.principal || {})
const other = computed(() => (data.value && data.value.other) || {})

const bucketAmt = (name) => {
  const b = overview.value.buckets && overview.value.buckets[name]
  return b ? b.amount : 0
}

const auditClean = computed(() =>
  !(audit.value.off_channel || []).length && !(audit.value.missed || []).length
)

const yoyText = computed(() => {
  const v = stats.value.yoy_avg_pct
  if (v == null) return '—'
  return (v > 0 ? '+' : '') + fmt(v) + '%'
})
const yoyStyle = computed(() => {
  const v = stats.value.yoy_avg_pct
  if (v == null) return {}
  return { color: v >= 0 ? '#34C759' : '#FF3B30' }
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await api.getIncomeAnalysis(year.value ? { year: year.value } : {})
    year.value = data.value.year || year.value
    years.value = data.value.years || years.value
    loading.value = false   // 必须先揭开 v-else 模板,图表容器才存在
    await nextTick()
    renderCharts()
  } catch (e) {
    error.value = e.message || '加载失败'
    ui.showError(e.message || '收入分析加载失败')
  } finally {
    loading.value = false
  }
}

function setYear(y) {
  if (year.value === y) return
  year.value = y
  load()
}

const yAxisMoney = () => ({
  type: 'value',
  axisLabel: { formatter: (v) => (Math.abs(v) >= 10000 ? (v / 10000) + '万' : v) },
})

function renderCharts() {
  const d = data.value
  if (!d || d.empty) return
  renderSalary()
  renderSaving()
  renderInvest()
  renderOther()
}

// keep-alive / 数据切换后 DOM 可能重建：实例绑旧节点则销毁重建；容器不在则销毁
function ensure(chart, el) {
  if (chart && (!el || chart.getDom() !== el)) { chart.dispose(); chart = null }
  if (!el) return null
  return chart || echarts.init(el)
}

function renderSalary() {
  salaryChart = ensure(salaryChart, salaryRef.value)
  if (!salaryChart) return
  const ms = salaryMonths.value
  const median = stats.value.median

  salaryChart.setOption({
    tooltip: {
      trigger: 'axis', axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const p = (params || [])[0]
        if (!p) return ''
        const m = ms[p.dataIndex]
        if (!m) return ''
        const bonus = m.is_bonus ? ' <span style="color:#FF9500;font-weight:600">含奖金</span>' : ''
        return `<b>${m.month}</b>${bonus}<br/>金额：¥${fmt(m.amount)}<br/>发薪日：${m.payday || '—'}<br/>${m.desc || ''}`
      },
    },
    grid: { left: 56, right: 16, top: 30, bottom: 50 },
    xAxis: { type: 'category', data: ms.map(m => m.month), axisLabel: { rotate: 45, fontSize: 10 } },
    yAxis: yAxisMoney(),
    series: [{
      name: '工资', type: 'bar', barMaxWidth: 26,
      data: ms.map(m => ({ value: m.amount, itemStyle: { color: m.is_bonus ? '#FF9500' : '#34C759' } })),
      markLine: median == null ? undefined : {
        silent: true, symbol: 'none',
        lineStyle: { type: 'dashed', color: '#8E8E93' },
        label: { formatter: '中位数 ¥' + fmt(median), fontSize: 10, color: '#8E8E93' },
        data: [{ yAxis: median }],
      },
    }],
  }, true)
}

function renderSaving() {
  savingChart = ensure(savingChart, savingRef.value)
  if (!savingChart) return
  const ms = salaryMonths.value.slice(-12)

  savingChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { top: 0, textStyle: { fontSize: 11 } },
    grid: { left: 56, right: 50, top: 36, bottom: 40 },
    xAxis: { type: 'category', data: ms.map(m => m.month), axisLabel: { rotate: 30, fontSize: 10 } },
    yAxis: [
      yAxisMoney(),
      { type: 'value', axisLabel: { formatter: '{value}%' }, splitLine: { show: false } },
    ],
    series: [
      {
        name: '工资', type: 'bar', barMaxWidth: 20, itemStyle: { color: '#34C759' },
        data: ms.map(m => m.amount),
        tooltip: { valueFormatter: (v) => '¥' + fmt(v) },
      },
      {
        name: '真实消费', type: 'bar', barMaxWidth: 20, itemStyle: { color: '#FF3B30' },
        data: ms.map(m => m.consume),
        tooltip: { valueFormatter: (v) => '¥' + fmt(v) },
      },
      {
        name: '结余率', type: 'line', yAxisIndex: 1, connectNulls: false,
        itemStyle: { color: '#007AFF' }, lineStyle: { color: '#007AFF' },
        data: ms.map(m => (m.saving_rate == null ? null : m.saving_rate)),  // null 点跳过
        tooltip: { valueFormatter: (v) => (v == null ? '—' : fmt(v) + '%') },
      },
    ],
  }, true)
}

function renderInvest() {
  investChart = ensure(investChart, investRef.value)
  if (!investChart) return
  const ms = investMonths.value

  investChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { top: 0, textStyle: { fontSize: 11 } },
    grid: { left: 56, right: 16, top: 36, bottom: 40 },
    xAxis: { type: 'category', data: ms.map(m => m.month), axisLabel: { rotate: 30, fontSize: 10 } },
    yAxis: yAxisMoney(),
    series: [
      {
        name: '当月收益', type: 'bar', barMaxWidth: 26, itemStyle: { color: '#5856D6' },
        data: ms.map(m => m.amount),
        tooltip: { valueFormatter: (v) => '¥' + fmt(v) },
      },
      {
        name: '累计收益', type: 'line', smooth: true,
        itemStyle: { color: '#AF52DE' }, lineStyle: { color: '#AF52DE' },
        data: ms.map(m => m.cum),
        tooltip: { valueFormatter: (v) => '¥' + fmt(v) },
      },
    ],
  }, true)
}

function renderOther() {
  otherChart = ensure(otherChart, otherRef.value)
  if (!otherChart) return
  const ms = other.value.months || []

  otherChart.setOption({
    tooltip: {
      trigger: 'axis', axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const p = (params || [])[0]
        return p ? `${p.name}<br/>¥${fmt(p.value)}` : ''
      },
    },
    grid: { left: 56, right: 16, top: 24, bottom: 40 },
    xAxis: { type: 'category', data: ms.map(m => m.month), axisLabel: { rotate: 30, fontSize: 10 } },
    yAxis: yAxisMoney(),
    series: [{
      name: '其他收入', type: 'bar', barMaxWidth: 26, itemStyle: { color: '#FF9500' },
      label: { show: true, position: 'top', fontSize: 10, color: '#8E8E93', formatter: (p) => fmtWan(p.value) },
      data: ms.map(m => m.amount),
    }],
  }, true)
}

function resize() {
  salaryChart && salaryChart.resize()
  savingChart && savingChart.resize()
  investChart && investChart.resize()
  otherChart && otherChart.resize()
}

onMounted(() => {
  load()
  window.addEventListener('resize', resize)
})
onActivated(() => {
  // keep-alive 切回标签后容器尺寸可能变化
  resize()
})
onUnmounted(() => {
  window.removeEventListener('resize', resize)
  salaryChart && salaryChart.dispose()
  savingChart && savingChart.dispose()
  investChart && investChart.dispose()
  otherChart && otherChart.dispose()
  salaryChart = savingChart = investChart = otherChart = null
})
</script>

<style scoped>
.income-page { max-width: 1200px; margin: 0 auto; }

.page-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  gap: 16px; margin-bottom: 20px; flex-wrap: wrap;
}
.page-title { font-size: 24px; font-weight: 600; color: var(--text-color); margin: 0 0 6px; }
.page-sub { font-size: 13px; color: var(--text-secondary, #8E8E93); margin: 0; max-width: 640px; line-height: 1.5; }

.year-side { display: flex; flex-direction: column; align-items: flex-end; gap: 6px; }
.year-filter { display: flex; gap: 6px; flex-wrap: wrap; justify-content: flex-end; }
.year-btn {
  padding: 6px 14px; border: 1px solid var(--border-color); background: var(--card-bg);
  color: var(--text-color); border-radius: var(--radius-sm); font-size: 13px; cursor: pointer;
  transition: all .2s;
}
.year-btn:hover { border-color: #34C759; }
.year-btn.active { background: #34C759; color: #fff; border-color: #34C759; }
.year-note { font-size: 11px; color: var(--text-secondary, #8E8E93); margin: 0; }

.state-box { padding: 60px 0; text-align: center; color: var(--text-secondary, #8E8E93); }
.state-box.error { color: #FF3B30; }

/* KPI */
.kpi-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 24px; }
.kpi-card {
  background: var(--card-bg); border: 1px solid var(--border-color); border-radius: var(--radius-md);
  padding: 16px; display: flex; align-items: center; gap: 12px;
}
.kpi-icon { width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0; }
.kpi-num { font-size: 19px; font-weight: 600; color: var(--text-color); line-height: 1.2; font-variant-numeric: tabular-nums; }
.kpi-strong { font-weight: 700; }
.kpi-label { font-size: 12px; color: var(--text-secondary, #8E8E93); }

.section { margin-bottom: 28px; }
.section-title { font-size: 16px; font-weight: 600; color: var(--text-color); margin: 0 0 14px; display: flex; align-items: center; gap: 8px; }
.section-title i { color: #34C759; font-size: 15px; }
.title-tag {
  font-size: 11px; font-weight: 500; color: var(--text-secondary, #8E8E93);
  background: var(--hover-bg, #F2F2F7); padding: 1px 8px; border-radius: 10px;
}

/* 图表卡 */
.chart-card { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 16px; margin-bottom: 14px; }
.chart-title { font-size: 14px; font-weight: 600; color: var(--text-color); margin: 0 0 10px; }
.chart { width: 100%; height: 300px; }
.chart-lg { height: 340px; }
.chart-sm { height: 240px; }
.dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin: 0 2px; vertical-align: middle; }

/* 指标条 */
.stat-strip { display: grid; grid-template-columns: repeat(6, 1fr); gap: 10px; margin-bottom: 14px; }
.stat-cell {
  background: var(--card-bg); border: 1px solid var(--border-color); border-radius: var(--radius-md);
  padding: 12px 14px; text-align: center;
}
.stat-num { font-size: 15px; font-weight: 600; color: var(--text-color); line-height: 1.3; font-variant-numeric: tabular-nums; }
.stat-label { font-size: 11px; color: var(--text-secondary, #8E8E93); margin-top: 3px; }

/* 黄条提示 */
.warn-banner {
  background: #FF95001A; border: 1px solid #FF950040; color: #FF9500;
  border-radius: var(--radius-md); padding: 10px 14px; font-size: 12.5px;
  margin-bottom: 14px; line-height: 1.6;
}
.warn-banner i { margin-right: 6px; }

/* 审计卡 */
.feed-card { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 16px; }
.audit-head { display: flex; justify-content: space-between; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 12px; }
.audit-title { font-size: 14px; font-weight: 600; color: var(--text-color); display: flex; align-items: center; gap: 8px; }
.audit-title i { color: #34C759; font-size: 14px; }
.channel-badge {
  font-size: 12px; font-weight: 600; color: #34C759; background: #34C75914;
  border: 1px solid #34C75940; padding: 2px 10px; border-radius: 10px;
}
.channel-badge i { margin-right: 4px; }
.audit-block { margin-bottom: 14px; }
.audit-block:last-child { margin-bottom: 0; }
.audit-sub { font-size: 13px; font-weight: 600; color: var(--text-color); margin: 0 0 8px; }
.ok-line { font-size: 14px; color: #34C759; display: flex; align-items: center; gap: 8px; padding: 8px 0; }
.card-note { font-size: 12px; color: var(--text-secondary, #8E8E93); margin: 10px 0 0; line-height: 1.5; }
.empty-hint { font-size: 13px; color: var(--text-secondary, #8E8E93); padding: 10px 2px; line-height: 1.6; }

/* 表格 */
.mini-table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
.mini-table th {
  text-align: left; font-size: 11px; font-weight: 600; color: var(--text-secondary, #8E8E93);
  padding: 6px 8px; border-bottom: 1px solid var(--border-color); white-space: nowrap;
}
.mini-table td { padding: 7px 8px; border-bottom: 1px solid var(--border-color); color: var(--text-color); }
.mini-table tr:last-child td { border-bottom: none; }
.mini-table .num { text-align: right; font-variant-numeric: tabular-nums; }
.mini-table .strong { font-weight: 600; }
.mini-table .ellipsis { max-width: 200px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

/* 理财双栏 */
.two-col { display: grid; grid-template-columns: 3fr 2fr; gap: 14px; align-items: start; }
.invest-total { margin-bottom: 12px; }
.principal-box { margin-top: 12px; border-top: 1px solid var(--border-color); padding-top: 10px; }
.principal-row { display: flex; justify-content: space-between; font-size: 13px; color: var(--text-secondary, #8E8E93); padding: 3px 0; }
.principal-row b { color: var(--text-color); font-variant-numeric: tabular-nums; }

/* 其他收入 */
.group-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 14px; }
.group-card { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 14px 16px; }
.group-head { display: flex; justify-content: space-between; align-items: baseline; gap: 8px; margin-bottom: 8px; }
.group-name { font-size: 14px; font-weight: 600; color: var(--text-color); }
.group-meta { font-size: 12px; color: #FF9500; font-weight: 600; white-space: nowrap; font-variant-numeric: tabular-nums; }
.top-list { list-style: none; margin: 0; padding: 0; }
.top-list li { display: flex; align-items: baseline; gap: 8px; font-size: 12px; padding: 4px 0; border-bottom: 1px dashed var(--border-color); }
.top-list li:last-child { border-bottom: none; }
.top-desc { flex: 1; color: var(--text-color); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.top-amt { color: var(--text-color); font-weight: 600; font-variant-numeric: tabular-nums; white-space: nowrap; }
.top-time { color: var(--text-secondary, #8E8E93); font-size: 11px; white-space: nowrap; }

@media (max-width: 1000px) {
  .kpi-row { grid-template-columns: repeat(2, 1fr); }
  .stat-strip { grid-template-columns: repeat(3, 1fr); }
  .two-col { grid-template-columns: 1fr; }
  .group-grid { grid-template-columns: 1fr; }
  .year-side { align-items: flex-start; }
  .mini-table .ellipsis { max-width: 120px; }
}
</style>
