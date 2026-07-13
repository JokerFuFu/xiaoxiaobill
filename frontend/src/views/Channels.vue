<template>
  <div class="channels-page">
    <!-- 页头 -->
    <div class="page-header">
      <div>
        <h1 class="page-title">渠道分析</h1>
        <p class="page-sub">按银行卡（储蓄 / 信用 · 区分卡号）、电子钱包、支付宝、微信等资金渠道，多维拆解你的钱从哪来、往哪去。</p>
      </div>
      <div class="year-filter">
        <button
          v-for="y in yearOptions"
          :key="y.value"
          class="year-btn"
          :class="{ active: year === y.value }"
          @click="setYear(y.value)"
        >{{ y.label }}</button>
      </div>
    </div>

    <div v-if="loading" class="state-box">数据加载中…</div>
    <div v-else-if="error" class="state-box error">{{ error }}</div>
    <div v-else-if="!data || data.totals.channel_count === 0" class="state-box">暂无渠道数据，请先在「设置」上传账单。</div>

    <template v-else>
      <!-- KPI 概览 -->
      <div class="kpi-row">
        <div class="kpi-card">
          <div class="kpi-icon" style="background:#FF950022;color:#FF9500"><i class="fas fa-layer-group"></i></div>
          <div><div class="kpi-num">{{ data.totals.channel_count }}</div><div class="kpi-label">资金渠道</div></div>
        </div>
        <div class="kpi-card">
          <div class="kpi-icon" style="background:#007AFF22;color:#007AFF"><i class="fas fa-credit-card"></i></div>
          <div><div class="kpi-num">{{ data.totals.card_count }}</div><div class="kpi-label">银行卡</div></div>
        </div>
        <div class="kpi-card">
          <div class="kpi-icon" style="background:#34C75922;color:#34C759"><i class="fas fa-wallet"></i></div>
          <div><div class="kpi-num">{{ data.totals.wallet_count }}</div><div class="kpi-label">电子钱包</div></div>
        </div>
        <div class="kpi-card">
          <div class="kpi-icon" style="background:#5856D622;color:#5856D6"><i class="fas fa-sitemap"></i></div>
          <div><div class="kpi-num">{{ data.totals.platform_count }}</div><div class="kpi-label">覆盖平台</div></div>
        </div>
        <div class="kpi-card wide">
          <div class="kpi-icon" style="background:#FF3B3022;color:#FF3B30"><i class="fas fa-yuan-sign"></i></div>
          <div><div class="kpi-num">¥{{ fmt(data.totals.expense) }}</div><div class="kpi-label">渠道总支出</div></div>
        </div>
      </div>

      <!-- 平台对比 -->
      <div class="section">
        <h2 class="section-title"><i class="fas fa-sitemap"></i> 平台维度（支出占比）</h2>
        <div class="platform-row">
          <div v-for="p in data.platforms" :key="p.platform" class="platform-card">
            <div class="platform-head">
              <span class="platform-dot" :style="{ background: p.color }"></span>
              <span class="platform-name">{{ p.name }}</span>
              <span class="platform-ratio">{{ p.expense_ratio }}%</span>
            </div>
            <div class="platform-amount">¥{{ fmt(p.expense) }}</div>
            <div class="bar"><div class="bar-fill" :style="{ width: p.expense_ratio + '%', background: p.color }"></div></div>
            <div class="platform-meta">
              <span><i class="fas fa-receipt"></i> {{ p.count }} 笔</span>
              <span><i class="fas fa-credit-card"></i> {{ p.card_count }} 渠道</span>
              <span v-if="p.income > 0"><i class="fas fa-arrow-down"></i> 收 ¥{{ fmt(p.income) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 信用 vs 储蓄 -->
      <div class="section">
        <h2 class="section-title"><i class="fas fa-balance-scale"></i> 信用 vs 储蓄/余额</h2>
        <div class="cd-row">
          <div class="cd-card credit">
            <div class="cd-head"><i class="fas fa-credit-card"></i> 信用支付<span class="cd-tag">信用卡 · 花呗 · 借呗</span></div>
            <div class="cd-amount">¥{{ fmt(data.credit_debit.credit.expense) }}</div>
            <div class="cd-meta">
              <span>占比 <b>{{ data.credit_debit.credit.ratio }}%</b></span>
              <span>{{ data.credit_debit.credit.count }} 笔</span>
              <span>客单价 ¥{{ fmt(data.credit_debit.credit.avg) }}</span>
            </div>
          </div>
          <div class="cd-versus">VS</div>
          <div class="cd-card debit">
            <div class="cd-head"><i class="fas fa-piggy-bank"></i> 储蓄/余额<span class="cd-tag">储蓄卡 · 余额 · 理财</span></div>
            <div class="cd-amount">¥{{ fmt(data.credit_debit.debit.expense) }}</div>
            <div class="cd-meta">
              <span>占比 <b>{{ data.credit_debit.debit.ratio }}%</b></span>
              <span>{{ data.credit_debit.debit.count }} 笔</span>
              <span>客单价 ¥{{ fmt(data.credit_debit.debit.avg) }}</span>
            </div>
          </div>
        </div>
        <div class="cd-bar">
          <div class="cd-bar-seg credit" :style="{ width: cdCreditPct + '%' }">{{ cdCreditPct }}%</div>
          <div class="cd-bar-seg debit" :style="{ width: (100 - cdCreditPct) + '%' }">{{ 100 - cdCreditPct }}%</div>
        </div>
      </div>

      <!-- 图表行 -->
      <div class="section">
        <div class="charts-grid">
          <div class="chart-card">
            <h3 class="chart-title">类型占比（支出）</h3>
            <div ref="kindPieRef" class="chart"></div>
          </div>
          <div class="chart-card">
            <h3 class="chart-title">各渠道支出占比</h3>
            <div ref="chanPieRef" class="chart"></div>
          </div>
        </div>
      </div>

      <!-- 月度堆叠 -->
      <div class="section">
        <div class="chart-card">
          <h3 class="chart-title">渠道月度支出趋势</h3>
          <div ref="monthlyRef" class="chart tall"></div>
        </div>
      </div>

      <!-- 渠道明细卡片 -->
      <div class="section">
        <h2 class="section-title"><i class="fas fa-list"></i> 资金渠道明细（{{ data.channels.length }}）</h2>
        <div class="channel-grid">
          <div v-for="c in data.channels" :key="c.key" class="channel-card">
            <div class="cc-top">
              <div class="cc-badge" :style="{ background: c.color }">
                <span v-if="c.group === '银行卡'">{{ c.bank }}</span>
                <i v-else :class="walletIcon(c.kind)"></i>
              </div>
              <div class="cc-id">
                <div class="cc-label">{{ c.label }}</div>
                <span class="cc-kind" :style="kindStyle(c.kind)">{{ c.kind }}</span>
              </div>
              <div class="cc-amount">
                <div class="cc-exp">¥{{ fmt(c.expense) }}</div>
                <div class="cc-ratio">{{ c.expense_ratio }}%</div>
              </div>
            </div>
            <div class="bar slim"><div class="bar-fill" :style="{ width: Math.min(100, c.expense_ratio) + '%', background: c.color }"></div></div>
            <div class="cc-stats">
              <span><i class="fas fa-receipt"></i> {{ c.expense_count }} 笔</span>
              <span><i class="fas fa-tag"></i> 均 ¥{{ fmt(c.avg) }}</span>
              <span><i class="fas fa-calendar-day"></i> {{ c.active_days }} 天</span>
            </div>
            <div v-if="c.transfer_in || c.transfer_out || c.internal || c.income" class="cc-flow">
              <span v-if="c.income">收入 ¥{{ fmt(c.income) }}</span>
              <span v-if="c.transfer_in">转入 ¥{{ fmt(c.transfer_in) }}</span>
              <span v-if="c.transfer_out">转出 ¥{{ fmt(c.transfer_out) }}</span>
              <span v-if="c.internal">搬运 ¥{{ fmt(c.internal) }}</span>
            </div>
            <div v-if="c.platform_breakdown.length" class="cc-plats">
              <span v-for="b in c.platform_breakdown" :key="b.platform" class="cc-plat">
                {{ b.platform }} · {{ b.count }}笔<template v-if="b.expense"> ¥{{ fmt(b.expense) }}</template>
              </span>
            </div>
            <div v-if="c.top_categories.length" class="cc-cats">
              <span v-for="t in c.top_categories" :key="t.name" class="cc-cat">{{ t.name }} ¥{{ fmt(t.value) }}</span>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import api from '@/api/client'

const loading = ref(true)
const error = ref('')
const data = ref(null)
const year = ref(null)

const yearOptions = [
  { label: '全部', value: null },
  { label: '2026', value: 2026 },
  { label: '2025', value: 2025 },
]

const kindPieRef = ref(null)
const chanPieRef = ref(null)
const monthlyRef = ref(null)
let kindPie = null, chanPie = null, monthly = null

const fmt = (v) => {
  const n = Number(v || 0)
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const cdCreditPct = computed(() => {
  if (!data.value) return 0
  const c = data.value.credit_debit.credit.expense
  const d = data.value.credit_debit.debit.expense
  const t = c + d
  return t > 0 ? Math.round(c / t * 100) : 0
})

const KIND_COLOR = {
  信用卡: '#FF3B30', 信用账户: '#FF6B5E', 储蓄卡: '#007AFF',
  余额账户: '#34C759', 理财账户: '#FF9500', 银行卡: '#5856D6', 未标注: '#9AA0A6',
}
const kindStyle = (k) => {
  const c = KIND_COLOR[k] || '#8E8E93'
  return { color: c, background: c + '1A', border: `1px solid ${c}55` }
}
const walletIcon = (kind) => {
  if (kind === '信用账户') return 'fas fa-credit-card'
  if (kind === '理财账户') return 'fas fa-piggy-bank'
  if (kind === '余额账户') return 'fas fa-wallet'
  if (kind === '未标注') return 'fas fa-question'
  return 'fas fa-coins'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await api.getChannelAnalysis(year.value ? { year: year.value } : {})
    await nextTick()
    renderCharts()
  } catch (e) {
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

function setYear(y) {
  if (year.value === y) return
  year.value = y
  load()
}

function renderCharts() {
  if (!data.value) return
  const d = data.value

  // 类型占比饼图
  if (kindPieRef.value) {
    const items = d.kind_summary.filter(k => k.expense > 0)
    kindPie = kindPie || echarts.init(kindPieRef.value)
    kindPie.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: ¥{c} ({d}%)' },
      legend: { bottom: 0, type: 'scroll' },
      series: [{
        type: 'pie', radius: ['42%', '68%'], center: ['50%', '44%'], avoidLabelOverlap: true,
        itemStyle: { borderColor: '#fff', borderWidth: 2, borderRadius: 4 },
        label: { formatter: '{b}\n{d}%', fontSize: 11 },
        data: items.map(k => ({ name: k.kind, value: k.expense, itemStyle: { color: k.color } })),
      }],
    })
  }

  // 渠道支出占比饼图（top10 + 其他）
  if (chanPieRef.value) {
    const ch = d.channels.filter(c => c.expense > 0)
    const top = ch.slice(0, 10)
    const rest = ch.slice(10).reduce((s, c) => s + c.expense, 0)
    const pieData = top.map(c => ({ name: c.label, value: c.expense, itemStyle: { color: c.color } }))
    if (rest > 0) pieData.push({ name: '其他', value: Number(rest.toFixed(2)), itemStyle: { color: '#C7C7CC' } })
    chanPie = chanPie || echarts.init(chanPieRef.value)
    chanPie.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: ¥{c} ({d}%)' },
      legend: { type: 'scroll', orient: 'vertical', right: 0, top: 'middle', textStyle: { fontSize: 11 } },
      series: [{
        type: 'pie', radius: ['40%', '66%'], center: ['38%', '50%'], avoidLabelOverlap: true,
        itemStyle: { borderColor: '#fff', borderWidth: 2, borderRadius: 4 },
        label: { show: false }, labelLine: { show: false },
        data: pieData,
      }],
    })
  }

  // 月度堆叠柱状图
  if (monthlyRef.value) {
    const m = d.monthly
    monthly = monthly || echarts.init(monthlyRef.value)
    monthly.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' },
        valueFormatter: (v) => '¥' + Number(v || 0).toLocaleString('zh-CN') },
      legend: { type: 'scroll', top: 0, textStyle: { fontSize: 11 } },
      grid: { left: 50, right: 16, top: 36, bottom: 50 },
      xAxis: { type: 'category', data: m.months, axisLabel: { rotate: 45, fontSize: 10 } },
      yAxis: { type: 'value', axisLabel: { formatter: (v) => v >= 10000 ? (v / 10000) + '万' : v } },
      series: m.series.map(s => ({
        name: s.label, type: 'bar', stack: 'total',
        itemStyle: { color: s.color }, emphasis: { focus: 'series' },
        data: s.data,
      })),
    })
  }
}

function resize() {
  kindPie && kindPie.resize()
  chanPie && chanPie.resize()
  monthly && monthly.resize()
}

onMounted(() => {
  load()
  window.addEventListener('resize', resize)
})
onUnmounted(() => {
  window.removeEventListener('resize', resize)
  kindPie && kindPie.dispose()
  chanPie && chanPie.dispose()
  monthly && monthly.dispose()
})
</script>

<style scoped>
.channels-page { max-width: 1200px; margin: 0 auto; }

.page-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  gap: 16px; margin-bottom: 20px; flex-wrap: wrap;
}
.page-title { font-size: 24px; font-weight: 600; color: var(--text-color); margin: 0 0 6px; }
.page-sub { font-size: 13px; color: var(--text-secondary, #8E8E93); margin: 0; max-width: 640px; line-height: 1.5; }

.year-filter { display: flex; gap: 6px; }
.year-btn {
  padding: 6px 14px; border: 1px solid var(--border-color); background: var(--card-bg);
  color: var(--text-color); border-radius: var(--radius-sm); font-size: 13px; cursor: pointer;
  transition: all .2s;
}
.year-btn:hover { border-color: var(--primary-color); }
.year-btn.active { background: var(--primary-color); color: #fff; border-color: var(--primary-color); }

.state-box { padding: 60px 0; text-align: center; color: var(--text-secondary, #8E8E93); }
.state-box.error { color: #FF3B30; }

/* KPI */
.kpi-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 24px; }
.kpi-card {
  background: var(--card-bg); border: 1px solid var(--border-color); border-radius: var(--radius-md);
  padding: 16px; display: flex; align-items: center; gap: 12px;
}
.kpi-icon { width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0; }
.kpi-num { font-size: 20px; font-weight: 600; color: var(--text-color); line-height: 1.2; }
.kpi-label { font-size: 12px; color: var(--text-secondary, #8E8E93); }

.section { margin-bottom: 28px; }
.section-title { font-size: 16px; font-weight: 600; color: var(--text-color); margin: 0 0 14px; display: flex; align-items: center; gap: 8px; }
.section-title i { color: #FF9500; font-size: 15px; }

/* 平台 */
.platform-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
.platform-card { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 18px; }
.platform-head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.platform-dot { width: 12px; height: 12px; border-radius: 50%; }
.platform-name { font-size: 15px; font-weight: 600; color: var(--text-color); }
.platform-ratio { margin-left: auto; font-size: 14px; font-weight: 600; color: var(--text-secondary, #8E8E93); }
.platform-amount { font-size: 24px; font-weight: 700; color: var(--text-color); margin-bottom: 10px; }
.platform-meta { display: flex; gap: 14px; flex-wrap: wrap; font-size: 12px; color: var(--text-secondary, #8E8E93); margin-top: 10px; }
.platform-meta i { margin-right: 3px; }

.bar { height: 8px; background: var(--hover-bg, #F2F2F7); border-radius: 4px; overflow: hidden; }
.bar.slim { height: 6px; }
.bar-fill { height: 100%; border-radius: 4px; transition: width .4s; }

/* 信用 vs 储蓄 */
.cd-row { display: flex; align-items: stretch; gap: 14px; margin-bottom: 12px; }
.cd-card { flex: 1; background: var(--card-bg); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 18px; }
.cd-card.credit { border-top: 3px solid #FF3B30; }
.cd-card.debit { border-top: 3px solid #007AFF; }
.cd-head { font-size: 14px; font-weight: 600; color: var(--text-color); display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.cd-head i { font-size: 16px; }
.cd-card.credit .cd-head i { color: #FF3B30; }
.cd-card.debit .cd-head i { color: #007AFF; }
.cd-tag { margin-left: auto; font-size: 11px; font-weight: 400; color: var(--text-secondary, #8E8E93); }
.cd-amount { font-size: 26px; font-weight: 700; color: var(--text-color); margin-bottom: 8px; }
.cd-meta { display: flex; gap: 16px; font-size: 12px; color: var(--text-secondary, #8E8E93); }
.cd-meta b { color: var(--text-color); }
.cd-versus { display: flex; align-items: center; font-size: 13px; font-weight: 700; color: #C7C7CC; }
.cd-bar { display: flex; height: 28px; border-radius: 8px; overflow: hidden; }
.cd-bar-seg { display: flex; align-items: center; justify-content: center; color: #fff; font-size: 12px; font-weight: 600; min-width: 36px; }
.cd-bar-seg.credit { background: #FF3B30; }
.cd-bar-seg.debit { background: #007AFF; }

/* 图表 */
.charts-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.chart-card { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 16px; }
.chart-title { font-size: 14px; font-weight: 600; color: var(--text-color); margin: 0 0 10px; }
.chart { width: 100%; height: 300px; }
.chart.tall { height: 380px; }

/* 渠道卡片 */
.channel-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(330px, 1fr)); gap: 14px; }
.channel-card { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 16px; }
.cc-top { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.cc-badge {
  width: 44px; height: 44px; border-radius: 10px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-size: 13px; font-weight: 700; letter-spacing: -.5px;
}
.cc-badge i { font-size: 18px; }
.cc-id { flex: 1; min-width: 0; }
.cc-label { font-size: 14px; font-weight: 600; color: var(--text-color); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cc-kind { display: inline-block; margin-top: 4px; padding: 1px 8px; border-radius: 10px; font-size: 11px; font-weight: 500; }
.cc-amount { text-align: right; flex-shrink: 0; }
.cc-exp { font-size: 17px; font-weight: 700; color: var(--text-color); }
.cc-ratio { font-size: 12px; color: var(--text-secondary, #8E8E93); }
.cc-stats { display: flex; gap: 14px; font-size: 12px; color: var(--text-secondary, #8E8E93); margin: 10px 0 8px; }
.cc-stats i { margin-right: 3px; }
.cc-flow { display: flex; gap: 10px; flex-wrap: wrap; font-size: 11px; color: #AF52DE; margin-bottom: 8px; }
.cc-plats { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 8px; }
.cc-plat { font-size: 11px; padding: 2px 8px; border-radius: 6px; background: var(--hover-bg, #F2F2F7); color: var(--text-secondary, #636366); }
.cc-cats { display: flex; gap: 6px; flex-wrap: wrap; }
.cc-cat { font-size: 11px; padding: 2px 8px; border-radius: 6px; background: #FF950014; color: #C77700; }

@media (max-width: 1000px) {
  .kpi-row { grid-template-columns: repeat(2, 1fr); }
  .platform-row { grid-template-columns: 1fr; }
  .charts-grid { grid-template-columns: 1fr; }
  .cd-row { flex-direction: column; }
  .cd-versus { justify-content: center; }
}
</style>
