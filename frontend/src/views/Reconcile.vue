<template>
  <div class="reconcile-page">
    <!-- 页头 -->
    <div class="page-header">
      <div>
        <h1 class="page-title">对账中心</h1>
        <p class="page-sub">把总流水一层层剥离到真实消费 / 真实收入，并审计跨渠道双算 —— 让口径可信是分析一切的前提。</p>
      </div>
      <div class="year-filter">
        <button
          v-for="y in years"
          :key="y"
          class="year-btn"
          :class="{ active: year === y }"
          @click="setYear(y)"
        >{{ y }}</button>
      </div>
    </div>

    <div v-if="loading" class="state-box">数据加载中…</div>
    <div v-else-if="error" class="state-box error">{{ error }}</div>
    <div v-else-if="!data || data.empty" class="state-box">暂无账单数据，请先在「设置」上传账单，再来对账。</div>

    <template v-else>
      <!-- KPI -->
      <div class="kpi-row">
        <div class="kpi-card">
          <div class="kpi-icon" style="background:#FF3B3022;color:#FF3B30"><i class="fas fa-cart-shopping"></i></div>
          <div>
            <div class="kpi-num" style="color:#FF3B30">¥{{ fmt(data.waterfall.real_expense) }}</div>
            <div class="kpi-label">真实消费</div>
          </div>
        </div>
        <div class="kpi-card">
          <div class="kpi-icon" style="background:#34C75922;color:#34C759"><i class="fas fa-sack-dollar"></i></div>
          <div>
            <div class="kpi-num" style="color:#34C759">¥{{ fmt(data.waterfall.real_income) }}</div>
            <div class="kpi-label">真实收入</div>
          </div>
        </div>
        <div class="kpi-card">
          <div class="kpi-icon" style="background:#8E8E9322;color:#8E8E93"><i class="fas fa-arrows-rotate"></i></div>
          <div>
            <div class="kpi-num">¥{{ fmt(internalScale) }}</div>
            <div class="kpi-label">内部流转 + 转账往来规模</div>
          </div>
        </div>
        <div class="kpi-card">
          <div class="kpi-icon" :style="suspectCount > 0 ? 'background:#FF950022;color:#FF9500' : 'background:#34C75922;color:#34C759'">
            <i class="fas fa-triangle-exclamation"></i>
          </div>
          <div>
            <div class="kpi-num" :style="suspectCount > 0 ? 'color:#FF9500' : ''">{{ suspectCount }}</div>
            <div class="kpi-label">疑似双算（组）<span v-if="suspectCount > 0" class="kpi-warn">待人工核对</span></div>
          </div>
        </div>
      </div>

      <!-- 口径瀑布 -->
      <div class="section">
        <h2 class="section-title"><i class="fas fa-filter"></i> 口径瀑布</h2>
        <div class="charts-grid">
          <div class="chart-card">
            <h3 class="chart-title">流出侧：总流出 → 真实消费</h3>
            <div ref="outflowRef" class="chart"></div>
            <p class="chart-note">总流出 ¥{{ fmt(data.waterfall.outflow.total) }}（{{ data.waterfall.outflow.count }} 笔），逐桶剥离非「消费」流出后，剩下的才是真实消费。</p>
          </div>
          <div class="chart-card">
            <h3 class="chart-title">流入侧：总流入 → 真实收入</h3>
            <div ref="inflowRef" class="chart"></div>
            <p class="chart-note">总流入 ¥{{ fmt(data.waterfall.inflow.total) }}（{{ data.waterfall.inflow.count }} 笔），真实收入 = 工资收入 + 投资收益 + 其他收入。</p>
          </div>
        </div>
        <p class="section-note">另有「不计收支」内部搬运 ¥{{ fmt(data.waterfall.neutral.total) }}（{{ data.waterfall.neutral.count }} 笔），不参与两侧统计。</p>
      </div>

      <!-- 资金性质明细 -->
      <div class="section">
        <h2 class="section-title"><i class="fas fa-tags"></i> 资金性质明细</h2>
        <div class="table-card">
          <table class="mini-table">
            <thead>
              <tr><th>资金性质</th><th class="num">合计金额</th><th class="num">笔数</th><th>方向分布</th></tr>
            </thead>
            <tbody>
              <tr v-for="n in data.nature_breakdown" :key="n.nature">
                <td class="strong">{{ n.nature }}</td>
                <td class="num strong">{{ money(n.total) }}</td>
                <td class="num">{{ n.count }}</td>
                <td>
                  <span
                    v-for="d in dirChips(n.dirs)"
                    :key="d.dir"
                    class="dir-chip"
                    :style="dirStyle(d.dir)"
                  >{{ d.dir }} ¥{{ fmt(d.amount) }} · {{ d.count }}笔</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 平台喂养对账 -->
      <div class="section">
        <h2 class="section-title"><i class="fas fa-right-left"></i> 平台喂养对账</h2>
        <div v-if="!data.feeds.platforms.length" class="empty-hint">没有可对账的平台喂养数据。</div>
        <div v-else class="feed-grid">
          <div v-for="p in data.feeds.platforms" :key="p.platform" class="feed-card">
            <div class="feed-head">
              <span class="feed-name"><i class="fas fa-mobile-screen"></i> {{ p.platform }}</span>
              <div class="feed-totals">
                <span>平台侧卡出资 <b>{{ money(p.platform_card_out_total) }}</b></span>
                <span class="vs">vs</span>
                <span>银行侧喂养 <b>{{ money(p.bank_feed_total) }}</b></span>
              </div>
            </div>
            <table class="mini-table">
              <thead>
                <tr><th>月份</th><th class="num">平台侧卡出资</th><th class="num">银行侧喂养</th><th class="num">覆盖率</th></tr>
              </thead>
              <tbody>
                <tr v-for="m in p.months" :key="m.month">
                  <td>{{ m.month }}</td>
                  <td class="num">{{ money(m.platform_card_out) }}</td>
                  <td class="num">{{ money(m.bank_feed) }}</td>
                  <td class="num"><span class="cov" :class="covClass(m.coverage)">{{ covText(m.coverage) }}</span></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <p class="section-note">
          {{ data.feeds.note }}
          <template v-if="data.feeds.bank_feed_unnamed_total > 0">
            另有未指明平台的银行喂养合计 ¥{{ fmt(data.feeds.bank_feed_unnamed_total) }}。
          </template>
        </p>
      </div>

      <!-- 信用卡对账 -->
      <div class="section">
        <h2 class="section-title"><i class="fas fa-credit-card"></i> 信用卡对账</h2>
        <div class="feed-card">
          <div class="feed-head">
            <span class="feed-name"><i class="fas fa-credit-card"></i> 消费 vs 还款</span>
            <div class="feed-totals">
              <span>信用卡消费 <b>{{ money(data.credit.consume_total) }}</b></span>
              <span class="vs">vs</span>
              <span>还款合计 <b>{{ money(data.credit.repay_total) }}</b></span>
            </div>
          </div>
          <table class="mini-table">
            <thead>
              <tr><th>月份</th><th class="num">信用卡消费</th><th class="num">当月还款</th><th class="num">次月还款</th></tr>
            </thead>
            <tbody>
              <tr v-for="m in data.credit.months" :key="m.month">
                <td>{{ m.month }}</td>
                <td class="num">{{ money(m.consume) }}</td>
                <td class="num">{{ money(m.repay_same) }}</td>
                <td class="num">{{ money(m.repay_next) }}</td>
              </tr>
            </tbody>
          </table>
          <p class="card-note">{{ data.credit.note }}</p>
        </div>
      </div>

      <!-- 疑似双算 -->
      <div class="section">
        <h2 class="section-title"><i class="fas fa-clone"></i> 疑似双算</h2>
        <div class="feed-card">
          <div v-if="!data.suspects.length" class="ok-line"><i class="fas fa-circle-check"></i> 未发现跨来源同日同金额的消费对 ✓</div>
          <template v-else>
            <p class="hint-line">以下交易在不同来源中同日同金额出现，可能被双算。确认是同一笔后，可在下方口径规则把银行侧那笔标为内部流转。</p>
            <div v-for="(s, i) in data.suspects" :key="s.date + '-' + s.amount + '-' + i" class="suspect-item">
              <div class="suspect-head">
                <span class="s-date"><i class="fas fa-calendar-day"></i> {{ s.date }}</span>
                <b class="s-amount">¥{{ fmt(s.amount) }}</b>
                <span class="s-count">{{ s.count }} 笔</span>
              </div>
              <table class="mini-table">
                <thead>
                  <tr><th>来源</th><th>对方</th><th>说明</th><th>方式</th></tr>
                </thead>
                <tbody>
                  <tr v-for="(r, j) in s.rows" :key="j">
                    <td>{{ r.source }}</td>
                    <td class="ellipsis">{{ r.counterparty || '—' }}</td>
                    <td class="ellipsis">{{ r.desc || '—' }}</td>
                    <td>{{ r.pay || '—' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </template>
        </div>
      </div>

      <!-- 口径规则 -->
      <div class="section">
        <h2 class="section-title"><i class="fas fa-sliders"></i> 口径规则（自定义资金性质）</h2>
        <div class="feed-card">
          <p class="hint-line">规则按顺序首条命中生效，优先级高于内置口径；保存后全站口径即时重算。</p>

          <div v-if="!rules.length" class="empty-hint">暂无自定义规则，可在下方添加一条试试。</div>
          <div v-for="(r, i) in rules" :key="i" class="rule-row">
            <span class="rule-chip">{{ r.field }}</span>
            <span class="rule-kw">包含「{{ r.contains }}」</span>
            <i class="fas fa-arrow-right rule-arrow"></i>
            <span class="rule-nature">{{ r.nature }}</span>
            <button class="icon-btn" title="删除该规则" @click="removeRule(i)"><i class="fas fa-trash-can"></i></button>
          </div>

          <div class="rule-add">
            <select v-model="newRule.field" class="ctl">
              <option v-for="f in fields" :key="f" :value="f">{{ f }}</option>
            </select>
            <input v-model="newRule.contains" class="ctl grow" placeholder="关键词，如「美团」" @keyup.enter="addRule" />
            <select v-model="newRule.nature" class="ctl">
              <option v-for="n in natures" :key="n" :value="n">{{ n }}</option>
            </select>
            <button class="btn-ghost" @click="addRule"><i class="fas fa-plus"></i> 添加</button>
          </div>

          <div class="rule-actions">
            <button class="btn-primary" :disabled="saving" @click="saveRules">
              <i class="fas fa-floppy-disk"></i> {{ saving ? '保存中…' : '保存规则' }}
            </button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, onActivated, nextTick } from 'vue'
import * as echarts from 'echarts'
import api from '@/api/client'
import { useUiStore } from '@/stores/ui'

defineOptions({ name: 'Reconcile' })

const ui = useUiStore()

const loading = ref(true)
const error = ref('')
const data = ref(null)
const year = ref(null)
const years = ref([])

// 口径规则（独立状态）
const rules = ref([])
const natures = ref([])
const fields = ref([])
const newRule = ref({ field: '', contains: '', nature: '' })
const saving = ref(false)

const outflowRef = ref(null)
const inflowRef = ref(null)
let outChart = null, inChart = null

const fmt = (v) => (v == null ? '—' : Number(v).toLocaleString('zh-CN', { maximumFractionDigits: 2 }))
const fmtWan = (v) => {
  const n = Number(v || 0)
  return Math.abs(n) >= 10000 ? (n / 10000).toFixed(2) + '万' : fmt(n)
}
const money = (v) => (v == null ? '—' : '¥' + fmt(v))
const round2 = (v) => Number(Number(v || 0).toFixed(2))

const REAL_INCOME = ['工资收入', '投资收益', '其他收入']
const INTERNAL_NATURES = ['内部流转', '转账往来']

const suspectCount = computed(() => (data.value && data.value.suspects ? data.value.suspects.length : 0))

const internalScale = computed(() => {
  if (!data.value || data.value.empty) return 0
  const pick = (buckets) => (buckets || [])
    .filter(b => INTERNAL_NATURES.includes(b.nature))
    .reduce((s, b) => s + (b.amount || 0), 0)
  return round2(pick(data.value.waterfall.outflow.buckets) + pick(data.value.waterfall.inflow.buckets))
})

const DIR_COLOR = { 支出: '#FF3B30', 收入: '#34C759', 转入: '#AF52DE', 转出: '#AF52DE', 不计收支: '#8E8E93' }
const DIR_ORDER = ['支出', '收入', '转入', '转出', '不计收支']
const dirChips = (dirs) => {
  if (!dirs) return []
  return DIR_ORDER
    .filter(d => dirs[d] && (dirs[d].amount || dirs[d].count))
    .map(d => ({ dir: d, amount: dirs[d].amount, count: dirs[d].count }))
}
const dirStyle = (dir) => {
  const c = DIR_COLOR[dir] || '#8E8E93'
  return { color: c, background: c + '14', border: `1px solid ${c}40` }
}

const covClass = (c) => {
  if (c == null) return 'cov-na'
  if (c >= 70) return 'cov-good'
  if (c >= 30) return 'cov-mid'
  return 'cov-bad'
}
const covText = (c) => (c == null ? '—' : fmt(c) + '%')

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await api.getReconcile(year.value ? { year: year.value } : {})
    year.value = data.value.year || year.value
    years.value = data.value.years || years.value
    loading.value = false   // 必须先揭开 v-else 模板,图表容器才存在
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

function waterfallOption(firstLabel, total, buckets, lastLabel, lastValue) {
  const labels = [firstLabel]
  const placeholder = [0]
  const values = [{ value: round2(total), itemStyle: { color: '#64748B' } }]
  let cum = 0
  buckets.forEach(b => {
    cum += b.amount || 0
    labels.push(b.nature)
    placeholder.push(round2(Math.max(0, total - cum)))
    values.push({ value: round2(b.amount || 0), itemStyle: { color: '#A3AECB' } })
  })
  labels.push(lastLabel)
  placeholder.push(0)
  values.push({ value: round2(lastValue), itemStyle: { color: '#5856D6' } })

  return {
    tooltip: {
      trigger: 'axis', axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const p = (params || []).find(x => x.seriesName === '金额')
        return p ? `${p.name}<br/>¥${fmt(p.value)}` : ''
      },
    },
    grid: { left: 56, right: 16, top: 28, bottom: 56 },
    xAxis: { type: 'category', data: labels, axisLabel: { interval: 0, rotate: 30, fontSize: 10 } },
    yAxis: { type: 'value', axisLabel: { formatter: (v) => Math.abs(v) >= 10000 ? (v / 10000) + '万' : v } },
    series: [
      {
        name: 'placeholder', type: 'bar', stack: 'wf',
        itemStyle: { color: 'rgba(0,0,0,0)' },
        emphasis: { itemStyle: { color: 'rgba(0,0,0,0)' } },
        tooltip: { show: false },
        data: placeholder,
      },
      {
        name: '金额', type: 'bar', stack: 'wf', barMaxWidth: 42,
        label: { show: true, position: 'top', fontSize: 10, color: '#8E8E93', formatter: (p) => fmtWan(p.value) },
        data: values,
      },
    ],
  }
}

function renderCharts() {
  const d = data.value
  if (!d || d.empty) return
  const wf = d.waterfall

  // keep-alive / 年份切换后 DOM 可能重建，实例绑定旧节点则重建实例
  if (outChart && outflowRef.value && outChart.getDom() !== outflowRef.value) { outChart.dispose(); outChart = null }
  if (inChart && inflowRef.value && inChart.getDom() !== inflowRef.value) { inChart.dispose(); inChart = null }

  if (outflowRef.value) {
    const buckets = (wf.outflow.buckets || []).filter(b => b.nature !== '消费')
    outChart = outChart || echarts.init(outflowRef.value)
    outChart.setOption(waterfallOption('总流出', wf.outflow.total, buckets, '真实消费', wf.real_expense), true)
  }
  if (inflowRef.value) {
    const buckets = (wf.inflow.buckets || []).filter(b => !REAL_INCOME.includes(b.nature))
    inChart = inChart || echarts.init(inflowRef.value)
    inChart.setOption(waterfallOption('总流入', wf.inflow.total, buckets, '真实收入', wf.real_income), true)
  }
}

// ===== 口径规则 =====
async function loadRules() {
  try {
    const r = await api.natureRules()
    rules.value = (r.rules || []).map(x => ({ ...x }))
    natures.value = r.natures || []
    fields.value = r.fields || []
    if (!newRule.value.field && fields.value.length) newRule.value.field = fields.value[0]
    if (!newRule.value.nature && natures.value.length) newRule.value.nature = natures.value[0]
  } catch (e) {
    ui.showError(e.message || '口径规则加载失败')
  }
}

function addRule() {
  const kw = (newRule.value.contains || '').trim()
  if (!kw) { ui.showError('请先填写匹配关键词'); return }
  if (!newRule.value.field || !newRule.value.nature) { ui.showError('请选择字段与资金性质'); return }
  rules.value.push({ field: newRule.value.field, contains: kw, nature: newRule.value.nature })
  newRule.value.contains = ''
}

function removeRule(i) {
  rules.value.splice(i, 1)
}

async function saveRules() {
  if (!confirm('保存后全站口径将立即重算，确定保存当前规则？')) return
  saving.value = true
  try {
    const r = await api.natureRulesSave(rules.value.map(x => ({ field: x.field, contains: x.contains, nature: x.nature })))
    if (r && r.rules) rules.value = r.rules.map(x => ({ ...x }))
    ui.showSuccess('口径规则已保存，全站口径已重算')
    await Promise.all([loadRules(), load()])
  } catch (e) {
    ui.showError(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

function resize() {
  outChart && outChart.resize()
  inChart && inChart.resize()
}

onMounted(() => {
  load()
  loadRules()
  window.addEventListener('resize', resize)
})
onActivated(() => {
  // keep-alive 切回标签后容器尺寸可能变化
  resize()
})
onUnmounted(() => {
  window.removeEventListener('resize', resize)
  outChart && outChart.dispose()
  inChart && inChart.dispose()
  outChart = null
  inChart = null
})
</script>

<style scoped>
.reconcile-page { max-width: 1200px; margin: 0 auto; }

.page-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  gap: 16px; margin-bottom: 20px; flex-wrap: wrap;
}
.page-title { font-size: 24px; font-weight: 600; color: var(--text-color); margin: 0 0 6px; }
.page-sub { font-size: 13px; color: var(--text-secondary, #8E8E93); margin: 0; max-width: 640px; line-height: 1.5; }

.year-filter { display: flex; gap: 6px; flex-wrap: wrap; }
.year-btn {
  padding: 6px 14px; border: 1px solid var(--border-color); background: var(--card-bg);
  color: var(--text-color); border-radius: var(--radius-sm); font-size: 13px; cursor: pointer;
  transition: all .2s;
}
.year-btn:hover { border-color: #5856D6; }
.year-btn.active { background: #5856D6; color: #fff; border-color: #5856D6; }

.state-box { padding: 60px 0; text-align: center; color: var(--text-secondary, #8E8E93); }
.state-box.error { color: #FF3B30; }

/* KPI */
.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px; }
.kpi-card {
  background: var(--card-bg); border: 1px solid var(--border-color); border-radius: var(--radius-md);
  padding: 16px; display: flex; align-items: center; gap: 12px;
}
.kpi-icon { width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0; }
.kpi-num { font-size: 20px; font-weight: 600; color: var(--text-color); line-height: 1.2; }
.kpi-label { font-size: 12px; color: var(--text-secondary, #8E8E93); }
.kpi-warn { margin-left: 6px; color: #FF9500; font-weight: 600; }

.section { margin-bottom: 28px; }
.section-title { font-size: 16px; font-weight: 600; color: var(--text-color); margin: 0 0 14px; display: flex; align-items: center; gap: 8px; }
.section-title i { color: #5856D6; font-size: 15px; }
.section-note { font-size: 12px; color: var(--text-secondary, #8E8E93); margin: 10px 2px 0; line-height: 1.6; }

/* 图表 */
.charts-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.chart-card { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 16px; }
.chart-title { font-size: 14px; font-weight: 600; color: var(--text-color); margin: 0 0 10px; }
.chart { width: 100%; height: 300px; }
.chart-note { font-size: 12px; color: var(--text-secondary, #8E8E93); margin: 8px 0 0; line-height: 1.5; }

/* 表格 */
.table-card, .feed-card { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 16px; }
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

.dir-chip {
  display: inline-block; margin: 2px 6px 2px 0; padding: 1px 8px;
  border-radius: 10px; font-size: 11px; font-weight: 500; white-space: nowrap;
}

/* 平台喂养 */
.feed-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.feed-head { display: flex; justify-content: space-between; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 12px; }
.feed-name { font-size: 14px; font-weight: 600; color: var(--text-color); display: flex; align-items: center; gap: 8px; }
.feed-name i { color: #5856D6; font-size: 14px; }
.feed-totals { display: flex; align-items: center; gap: 10px; font-size: 12px; color: var(--text-secondary, #8E8E93); flex-wrap: wrap; }
.feed-totals b { color: var(--text-color); font-variant-numeric: tabular-nums; }
.feed-totals .vs { font-size: 11px; font-weight: 700; color: #C7C7CC; }
.card-note { font-size: 12px; color: var(--text-secondary, #8E8E93); margin: 10px 0 0; line-height: 1.5; }

.cov { display: inline-block; min-width: 44px; text-align: center; padding: 1px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; }
.cov-na { background: var(--hover-bg, #F2F2F7); color: var(--text-secondary, #8E8E93); }
.cov-good { background: #34C7591A; color: #34C759; }
.cov-mid { background: #FF95001A; color: #FF9500; }
.cov-bad { background: #FF3B301A; color: #FF3B30; }

/* 疑似双算 */
.ok-line { font-size: 14px; color: #34C759; display: flex; align-items: center; gap: 8px; padding: 8px 0; }
.hint-line { font-size: 12px; color: var(--text-secondary, #8E8E93); margin: 0 0 12px; line-height: 1.6; }
.suspect-item { border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 12px 14px; margin-bottom: 12px; }
.suspect-item:last-child { margin-bottom: 0; }
.suspect-head { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; font-size: 13px; }
.s-date { color: var(--text-secondary, #8E8E93); }
.s-date i { margin-right: 4px; color: #FF9500; }
.s-amount { font-size: 15px; color: var(--text-color); font-variant-numeric: tabular-nums; }
.s-count { font-size: 11px; padding: 1px 8px; border-radius: 10px; background: #FF95001A; color: #FF9500; font-weight: 600; }

/* 口径规则 */
.empty-hint { font-size: 13px; color: var(--text-secondary, #8E8E93); padding: 10px 2px; }
.rule-row {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  padding: 8px 10px; border: 1px solid var(--border-color); border-radius: var(--radius-md);
  margin-bottom: 8px; font-size: 13px;
}
.rule-chip { padding: 1px 8px; border-radius: 6px; background: #5856D614; color: #5856D6; font-size: 12px; font-weight: 600; }
.rule-kw { color: var(--text-color); }
.rule-arrow { color: #C7C7CC; font-size: 12px; }
.rule-nature { font-weight: 600; color: var(--text-color); }
.icon-btn {
  margin-left: auto; border: none; background: transparent; color: var(--text-secondary, #8E8E93);
  cursor: pointer; padding: 4px 6px; border-radius: 6px; font-size: 13px; transition: all .2s;
}
.icon-btn:hover { color: #FF3B30; background: #FF3B3014; }

.rule-add { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin: 14px 0 0; }
.ctl {
  padding: 7px 10px; border: 1px solid var(--border-color); border-radius: var(--radius-sm);
  background: var(--card-bg); color: var(--text-color); font-size: 13px; outline: none;
}
.ctl:focus { border-color: #5856D6; }
.ctl.grow { flex: 1; min-width: 160px; }
.btn-ghost {
  padding: 7px 14px; border: 1px solid #5856D6; background: transparent; color: #5856D6;
  border-radius: var(--radius-sm); font-size: 13px; cursor: pointer; transition: all .2s;
}
.btn-ghost:hover { background: #5856D614; }
.rule-actions { margin-top: 14px; display: flex; justify-content: flex-end; }
.btn-primary {
  padding: 8px 18px; border: none; background: #5856D6; color: #fff;
  border-radius: var(--radius-sm); font-size: 13px; font-weight: 600; cursor: pointer; transition: opacity .2s;
}
.btn-primary:hover { opacity: .88; }
.btn-primary:disabled { opacity: .5; cursor: not-allowed; }

@media (max-width: 1000px) {
  .kpi-row { grid-template-columns: repeat(2, 1fr); }
  .charts-grid { grid-template-columns: 1fr; }
  .feed-grid { grid-template-columns: 1fr; }
  .mini-table .ellipsis { max-width: 120px; }
}
</style>
