<template>
  <div class="annual-page">
    <div class="head-row">
      <h1 class="page-title"><i class="fas fa-gift" style="color:#FF2D55"></i> 年度账单</h1>
      <div class="head-actions">
        <select v-if="data.years && data.years.length" v-model="year" class="year-sel" @change="reload">
          <option v-for="y in data.years" :key="y" :value="y">{{ y }} 年</option>
        </select>
        <button v-if="!empty && !loading" class="share-btn" :disabled="sharing" @click="shareImage">
          <i class="fas fa-image"></i> {{ sharing ? '生成中…' : '保存为图片' }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="state-box">加载中…</div>
    <div v-else-if="empty" class="state-box">还没有账单数据，先去上传。</div>

    <!-- 报告主体(分享时截这一块) -->
    <div v-else ref="reportRef" class="report">
      <div class="report-brand">{{ year }} 年度账单 · 小遥账单助手</div>

      <!-- Hero -->
      <div class="hero">
        <div class="hero-item">
          <div class="hero-label">真实消费</div>
          <div class="hero-num red">¥{{ fmt(data.real_expense) }}</div>
          <div class="hero-foot">{{ data.tx_count }} 笔 · 已剔除转账/还款/投资</div>
        </div>
        <div class="hero-item">
          <div class="hero-label">真实收入</div>
          <div class="hero-num green">¥{{ fmt(data.real_income) }}</div>
          <div class="hero-foot">工资 + 理财 + 其他</div>
        </div>
        <div class="hero-item">
          <div class="hero-label">{{ data.saving >= 0 ? '年度结余' : '年度透支' }}</div>
          <div class="hero-num" :class="data.saving >= 0 ? 'green' : 'red'">¥{{ fmt(Math.abs(data.saving)) }}</div>
          <div class="hero-foot" v-if="data.saving_rate != null">储蓄率 {{ data.saving_rate }}%</div>
        </div>
        <div class="hero-item" v-if="data.net_worth">
          <div class="hero-label">净资产</div>
          <div class="hero-num">¥{{ fmt(data.net_worth.net) }}</div>
          <div class="hero-foot">截至 {{ data.net_worth.date }}</div>
        </div>
      </div>

      <!-- AI 年度小结 -->
      <div class="card narrative-card">
        <div class="card-head"><h3><i class="fas fa-feather-pointed" style="color:#AF52DE"></i> 年度小结</h3>
          <button v-if="aiEnabled" class="mini-btn" :disabled="genBusy" @click="genNarrative(true)">
            <i class="fas fa-rotate"></i> {{ narrative ? '重新生成' : '生成' }}
          </button>
        </div>
        <div v-if="narrative" class="narrative md" v-html="renderMd(narrative.summary)"></div>
        <div v-else-if="!aiEnabled" class="narr-empty">配置 AI 后可一键生成有温度的年度小结（设置 → AI 与模型）。下方数据图表无需 AI 即可查看。</div>
        <div v-else class="narr-empty">
          <button class="gen-btn" :disabled="genBusy" @click="genNarrative(false)">
            <i class="fas fa-wand-magic-sparkles"></i> {{ genBusy ? 'AI 撰写中…（约 30 秒）' : '生成我的年度小结' }}
          </button>
        </div>
        <p v-if="genErr" class="err">{{ genErr }}</p>
      </div>

      <!-- 逐月消费 -->
      <div class="card">
        <div class="card-head"><h3><i class="fas fa-chart-column" style="color:#5856D6"></i> 逐月消费</h3>
          <span class="muted" v-if="data.peak_month">最高 {{ data.peak_month.month }} 月 ¥{{ fmt(data.peak_month.amount) }}</span></div>
        <div ref="chartRef" class="annual-chart"></div>
      </div>

      <div class="grid2">
        <!-- top 分类 -->
        <div class="card">
          <div class="card-head"><h3><i class="fas fa-tags" style="color:#FF9500"></i> 钱花在哪</h3></div>
          <div v-for="(c, i) in data.top_categories" :key="i" class="bar-row">
            <span class="bar-name">{{ c.category }}</span>
            <div class="bar-track"><div class="bar-fill" :style="{ width: barPct(c.amount) + '%' }"></div></div>
            <span class="bar-amt">¥{{ fmt(c.amount) }}</span>
          </div>
        </div>
        <!-- 最大单笔 -->
        <div class="card">
          <div class="card-head"><h3><i class="fas fa-fire" style="color:#FF3B30"></i> 最大单笔</h3></div>
          <div v-for="(b, i) in data.biggest" :key="i" class="big-row">
            <div class="big-main"><span class="big-amt">¥{{ fmt(b.amount) }}</span> <span class="big-cat">{{ b.category }}</span></div>
            <div class="big-sub">{{ b.date }} · {{ b.desc }}</div>
          </div>
        </div>
      </div>

      <!-- 消费画像 -->
      <div class="card" v-if="data.profile">
        <div class="card-head"><h3><i class="fas fa-id-badge" style="color:#34C759"></i> 消费画像</h3></div>
        <div class="profile-grid">
          <div class="pf"><div class="pf-v">{{ data.profile.active_days }}</div><div class="pf-l">天有消费</div></div>
          <div class="pf"><div class="pf-v">¥{{ fmt(data.profile.avg_per_active_day) }}</div><div class="pf-l">消费日均花</div></div>
          <div class="pf" v-if="data.profile.peak_weekday"><div class="pf-v">{{ data.profile.peak_weekday }}</div><div class="pf-l">最爱花钱</div></div>
          <div class="pf" v-if="data.profile.peak_hour != null"><div class="pf-v">{{ data.profile.peak_hour }}:00</div><div class="pf-l">高峰时段</div></div>
          <div class="pf" v-if="data.profile.busiest_day"><div class="pf-v sm">{{ data.profile.busiest_day }}</div><div class="pf-l">花得最多的一天 ¥{{ fmt(data.profile.busiest_day_amount) }}</div></div>
          <div class="pf" v-if="data.profile.top_merchant"><div class="pf-v sm">{{ data.profile.top_merchant.name }}</div><div class="pf-l">最常光顾 {{ data.profile.top_merchant.count }} 次</div></div>
        </div>
      </div>

      <!-- 固定开销 / 境外 / 异常 -->
      <div class="grid3">
        <div class="card mini" v-if="data.subscriptions && data.subscriptions.count">
          <div class="mini-h"><i class="fas fa-repeat" style="color:#5856D6"></i> 订阅/定期</div>
          <div class="mini-v">¥{{ fmt(data.subscriptions.monthly_total) }}<span>/月</span></div>
          <div class="mini-f">{{ data.subscriptions.count }} 项 · 年 ¥{{ fmt(data.subscriptions.annual_total) }}</div>
          <router-link to="/analysis?tab=recurring" class="mini-link">查看明细 →</router-link>
        </div>
        <div class="card mini" v-if="data.overseas && data.overseas.count">
          <div class="mini-h"><i class="fas fa-earth-asia" style="color:#007AFF"></i> 境外消费</div>
          <div class="mini-v">¥{{ fmt(data.overseas.total_cny) }}</div>
          <div class="mini-f">{{ data.overseas.count }} 笔{{ data.overseas.by_currency && data.overseas.by_currency[0] ? ' · 主要 ' + data.overseas.by_currency[0].currency : '' }}</div>
          <router-link to="/analysis?tab=overseas" class="mini-link">查看明细 →</router-link>
        </div>
        <div class="card mini" v-if="data.anomalies && data.anomalies.count">
          <div class="mini-h"><i class="fas fa-triangle-exclamation" style="color:#FF9500"></i> 异常提醒</div>
          <div class="mini-v">{{ data.anomalies.count }}<span> 条</span></div>
          <div class="mini-f">{{ data.anomalies.top && data.anomalies.top[0] ? data.anomalies.top[0].title : '' }}</div>
          <router-link to="/" class="mini-link">首页查看 →</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import api from '@/api/client'

const loading = ref(true)
const empty = ref(false)
const year = ref(0)
const data = ref({ years: [] })
const narrative = ref(null)
const aiEnabled = ref(false)
const genBusy = ref(false)
const genErr = ref('')
const sharing = ref(false)
const chartRef = ref(null)
const reportRef = ref(null)
let chart = null

function fmt(v) { return (v || 0).toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 2 }) }
function renderMd(t) {
  const html = marked.parse(t || '', { breaks: true })
  return DOMPurify.sanitize(html, { FORBID_TAGS: ['style', 'script', 'iframe'], FORBID_ATTR: ['onerror', 'onclick'] })
}
function barPct(amt) {
  const max = (data.value.top_categories && data.value.top_categories[0]) ? data.value.top_categories[0].amount : 1
  return Math.max(3, Math.round(amt / max * 100))
}

function renderChart() {
  if (!chartRef.value || !data.value.monthly || !data.value.monthly.length) return
  if (!chart) chart = echarts.init(chartRef.value)
  const m = data.value.monthly
  chart.setOption({
    grid: { left: 8, right: 12, top: 18, bottom: 24, containLabel: true },
    tooltip: { trigger: 'axis', valueFormatter: v => '¥' + fmt(v) },
    xAxis: { type: 'category', data: m.map(x => x.month + '月'), axisLabel: { fontSize: 11, color: '#999' } },
    yAxis: { type: 'value', axisLabel: { fontSize: 10, color: '#999' }, splitLine: { lineStyle: { color: '#f0f0f3' } } },
    series: [{ type: 'bar', data: m.map(x => x.amount), itemStyle: { color: '#5856D6', borderRadius: [5, 5, 0, 0] }, barMaxWidth: 34 }],
  })
}

async function reload() {
  loading.value = true; genErr.value = ''
  try {
    const r = await api.getAnnualReport(year.value ? { year: year.value } : {})
    aiEnabled.value = !!r.ai_enabled
    if (!r.data || r.data.empty) {
      // 该年无数据但其它年有
      if (r.data && r.data.years && r.data.years.length) { data.value = r.data; empty.value = false }
      else empty.value = true
    } else {
      empty.value = false
      data.value = r.data
      year.value = r.data.year
      narrative.value = r.narrative || null
      await nextTick(); renderChart()
    }
  } catch (e) { empty.value = true }
  finally { loading.value = false }
}

async function genNarrative(force) {
  genBusy.value = true; genErr.value = ''
  try {
    const r = await api.genAnnualNarrative({ year: year.value, force })
    narrative.value = r.narrative
  } catch (e) {
    genErr.value = e.message || '生成失败，请稍后重试'
  } finally { genBusy.value = false }
}

async function shareImage() {
  if (!reportRef.value) return
  sharing.value = true
  try {
    const { default: html2canvas } = await import('html2canvas')
    const canvas = await html2canvas(reportRef.value, { scale: 2, useCORS: true, backgroundColor: '#f5f7fa', logging: false })
    const link = document.createElement('a')
    link.download = `年度账单_${year.value}.png`
    link.href = canvas.toDataURL('image/png')
    link.click()
  } catch (e) { genErr.value = '生成图片失败：' + (e.message || '') }
  finally { sharing.value = false }
}

onMounted(reload)
window.addEventListener('resize', () => chart && chart.resize())
</script>

<style scoped>
.annual-page { max-width: 1100px; margin: 0 auto; }
.head-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; flex-wrap: wrap; gap: 10px; }
.page-title { font-size: 22px; margin: 0; display: flex; align-items: center; gap: 9px; }
.head-actions { display: flex; gap: 10px; }
.year-sel { height: 38px; border: 1px solid #d2d2d7; border-radius: 9px; padding: 0 12px; font-size: 14px; background: #fff; }
.share-btn { height: 38px; border: none; border-radius: 9px; background: #1d1d1f; color: #fff; padding: 0 16px; font-size: 14px; cursor: pointer; }
.share-btn:disabled { opacity: .6; }
.state-box { text-align: center; color: #86868b; padding: 70px 20px; }
.muted { color: #a0a0a8; font-size: 13px; }
.report { display: flex; flex-direction: column; gap: 14px; }
.report-brand { font-size: 12px; color: #b0b0b8; letter-spacing: .5px; }
.hero { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px;
  background: linear-gradient(135deg, #1d1d1f 0%, #3a3a3f 100%); border-radius: 18px; padding: 22px 24px; }
.hero-item { color: #fff; }
.hero-label { font-size: 13px; opacity: .7; }
.hero-num { font-size: 26px; font-weight: 700; margin: 4px 0 2px; }
.hero-num.red { color: #FF6B6B; }
.hero-num.green { color: #4ADE80; }
.hero-foot { font-size: 11px; opacity: .55; }
.card { background: #fff; border: 1px solid #ecedf1; border-radius: 16px; padding: 18px 20px; }
.card-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.card-head h3 { font-size: 16px; margin: 0; display: flex; align-items: center; gap: 8px; }
.mini-btn, .gen-btn { border: none; border-radius: 8px; cursor: pointer; }
.mini-btn { background: #f0eefe; color: #5856D6; font-size: 13px; padding: 6px 12px; }
.mini-btn:disabled { opacity: .6; }
.narrative-card { border-color: #ece8fb; background: #fcfbff; }
.narrative.md { font-size: 14.5px; line-height: 1.8; color: #2c2c2e; }
.narrative.md :deep(strong) { color: #5856D6; }
.narrative.md :deep(h1), .narrative.md :deep(h2), .narrative.md :deep(h3) { font-size: 15px; margin: 12px 0 6px; }
.narr-empty { color: #86868b; font-size: 14px; padding: 8px 0; }
.gen-btn { background: linear-gradient(135deg, #AF52DE, #5856D6); color: #fff; font-size: 15px; padding: 12px 22px; }
.gen-btn:disabled { opacity: .7; }
.err { color: #ff3b30; font-size: 13px; margin: 10px 0 0; }
.annual-chart { height: 260px; width: 100%; }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.bar-row { display: flex; align-items: center; gap: 10px; padding: 5px 0; }
.bar-name { width: 84px; font-size: 13px; color: #444; flex-shrink: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.bar-track { flex: 1; height: 9px; background: #f0f0f3; border-radius: 6px; overflow: hidden; }
.bar-fill { height: 100%; background: linear-gradient(90deg, #FF9500, #FFCC00); border-radius: 6px; }
.bar-amt { width: 84px; text-align: right; font-size: 13px; color: #1d1d1f; font-weight: 500; flex-shrink: 0; }
.big-row { padding: 8px 0; border-bottom: 1px solid #f4f4f7; }
.big-row:last-child { border-bottom: none; }
.big-main { display: flex; align-items: baseline; gap: 8px; }
.big-amt { font-size: 17px; font-weight: 600; color: #FF3B30; }
.big-cat { font-size: 13px; color: #86868b; }
.big-sub { font-size: 12px; color: #a0a0a8; margin-top: 2px; }
.profile-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
.pf { background: #f7f8fa; border-radius: 12px; padding: 14px; text-align: center; }
.pf-v { font-size: 20px; font-weight: 700; color: #1d1d1f; }
.pf-v.sm { font-size: 14px; }
.pf-l { font-size: 12px; color: #86868b; margin-top: 4px; }
.grid3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
.card.mini { padding: 16px 18px; }
.mini-h { font-size: 13px; color: #555; display: flex; align-items: center; gap: 6px; }
.mini-v { font-size: 24px; font-weight: 700; color: #1d1d1f; margin: 8px 0 2px; }
.mini-v span { font-size: 13px; color: #a0a0a8; font-weight: 400; }
.mini-f { font-size: 12px; color: #a0a0a8; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mini-link { font-size: 12px; color: #007AFF; text-decoration: none; margin-top: 8px; display: inline-block; }
@media (max-width: 900px) { .hero, .profile-grid, .grid3 { grid-template-columns: repeat(2, 1fr); } .grid2 { grid-template-columns: 1fr; } }
@media (max-width: 560px) { .hero { grid-template-columns: 1fr; } }
</style>
