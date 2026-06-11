<template>
  <div class="networth-page">
    <!-- 页头 + 子页签 -->
    <div class="page-header">
      <div>
        <h1 class="page-title">资产负债</h1>
        <p class="page-sub">资产是存量，流水是流量 —— 净资产靠余额快照，收入是它的进水口。</p>
      </div>
      <div class="header-right">
        <div class="nw-tabs">
          <button class="nw-tab" :class="{ active: tab === 'sheet' }" @click="tab = 'sheet'">
            <i class="fas fa-scale-balanced"></i> 资产负债表
          </button>
          <button class="nw-tab" :class="{ active: tab === 'income' }" @click="tab = 'income'">
            <i class="fas fa-sack-dollar"></i> 收入分析
          </button>
        </div>
        <button
          v-if="tab === 'sheet'"
          class="primary-btn"
          :disabled="!data || !data.accounts.length"
          @click="toggleForm"
        ><i class="fas fa-plus"></i> 记一笔快照</button>
      </div>
    </div>

    <!-- 收入分析子页(keep-alive 保活) -->
    <keep-alive>
      <IncomeView v-if="tab === 'income'" />
    </keep-alive>

    <div v-show="tab === 'sheet'">
    <div v-if="loading" class="state-box">数据加载中…</div>
    <div v-else-if="error" class="state-box error">{{ error }}</div>

    <!-- 空状态：还没有账户 -->
    <div v-else-if="!data.accounts.length" class="card empty-card">
      <div class="empty-icon"><i class="fas fa-scale-balanced"></i></div>
      <h3 class="empty-title">从添加第一个账户开始</h3>
      <div class="empty-steps">
        <div class="empty-step"><span class="step-no">①</span> 添加你的资金账户</div>
        <i class="fas fa-arrow-right step-arrow"></i>
        <div class="empty-step"><span class="step-no">②</span> 定期（如每月 1 号）记录各账户余额</div>
        <i class="fas fa-arrow-right step-arrow"></i>
        <div class="empty-step"><span class="step-no">③</span> 看净资产趋势，并用流水解释变化</div>
      </div>
      <div class="add-row">
        <input v-model.trim="newAccName" class="text-input" placeholder="账户名称，如「招行储蓄卡」" @keyup.enter="addAccount" />
        <select v-model="newAccType" class="select-input">
          <option v-for="t in data.account_types" :key="t" :value="t">{{ t }}</option>
        </select>
        <button class="primary-btn small" :disabled="!newAccName || adding" @click="addAccount">添加</button>
      </div>
    </div>

    <template v-else>
      <!-- KPI（取 trend 最后一点） -->
      <div v-if="latest" class="kpi-row">
        <div class="kpi-card">
          <div class="kpi-icon" style="background:#34C75922;color:#34C759"><i class="fas fa-scale-balanced"></i></div>
          <div><div class="kpi-num big">¥{{ fmt(latest.net) }}</div><div class="kpi-label">净资产（{{ latest.date }}）</div></div>
        </div>
        <div class="kpi-card">
          <div class="kpi-icon" style="background:#34C75922;color:#34C759"><i class="fas fa-piggy-bank"></i></div>
          <div><div class="kpi-num green">¥{{ fmt(latest.assets) }}</div><div class="kpi-label">总资产</div></div>
        </div>
        <div class="kpi-card">
          <div class="kpi-icon" style="background:#FF3B3022;color:#FF3B30"><i class="fas fa-credit-card"></i></div>
          <div><div class="kpi-num red">¥{{ fmt(latest.liabilities) }}</div><div class="kpi-label">总负债</div></div>
        </div>
        <div class="kpi-card">
          <div class="kpi-icon" style="background:#5856D622;color:#5856D6"><i class="fas fa-camera"></i></div>
          <div><div class="kpi-num">{{ data.snapshots.length }}</div><div class="kpi-label">快照次数</div></div>
        </div>
      </div>

      <!-- 记一笔快照 -->
      <div v-if="showForm" class="card snap-form">
        <h3 class="card-title"><i class="fas fa-camera"></i> 记一笔快照</h3>
        <div class="form-meta">
          <label class="form-label">快照日期</label>
          <input v-model="form.date" type="date" class="text-input date-input" />
          <span class="form-hint">同一天重复保存会覆盖当天快照</span>
        </div>
        <div class="snap-accounts">
          <div v-for="acc in data.accounts" :key="acc.id" class="acc-row">
            <div class="acc-name">
              <span class="acc-label">{{ acc.name }}</span>
              <span class="type-badge" :class="{ liab: isLiability(acc) }">{{ acc.type }}</span>
            </div>
            <div class="acc-input-wrap">
              <input
                v-model="form.balances[acc.id]"
                type="number" step="0.01" min="0"
                class="num-input" :class="{ 'liab-input': isLiability(acc) }"
                :placeholder="isLiability(acc) ? '欠款金额（正数）' : '账户余额'"
              />
              <span v-if="isLiability(acc)" class="liab-tag">欠款</span>
            </div>
          </div>
        </div>
        <div class="form-meta">
          <label class="form-label">备注</label>
          <input v-model.trim="form.note" class="text-input note-input" placeholder="选填，如「发薪后」" />
        </div>
        <div class="form-actions">
          <button class="primary-btn" :disabled="saving" @click="saveSnapshot">{{ saving ? '保存中…' : '保存快照' }}</button>
          <button class="ghost-btn" @click="showForm = false">取消</button>
        </div>
      </div>

      <!-- 双图 -->
      <div v-if="data.trend.length" class="charts-grid">
        <div class="card chart-card">
          <h3 class="card-title"><i class="fas fa-chart-line"></i> 净资产趋势</h3>
          <div ref="trendRef" class="chart"></div>
        </div>
        <div class="card chart-card">
          <h3 class="card-title"><i class="fas fa-chart-pie"></i> 最新资产构成（{{ latest.date }}）</h3>
          <div ref="pieRef" class="chart"></div>
          <div v-if="latestLiabs.length" class="pie-liabs">
            <span v-for="l in latestLiabs" :key="l.type" class="pie-liab">{{ l.type }} 欠 ¥{{ fmt(l.amount) }}</span>
          </div>
        </div>
      </div>

      <!-- 流水解释 -->
      <div class="card explain-card">
        <h3 class="card-title"><i class="fas fa-diagram-project"></i> 流水如何解释净资产变化</h3>
        <div v-if="!data.explain.length" class="card-empty">记录两次以上快照后，这里会用流水拆解每段净资产变化。</div>
        <template v-else>
          <div class="table-wrap">
            <table class="explain-table">
              <thead>
                <tr>
                  <th>期间</th>
                  <th class="num">Δ净资产</th>
                  <th class="num">真实收入</th>
                  <th class="num">真实消费</th>
                  <th class="num">往来净额</th>
                  <th class="num">退款报销</th>
                  <th class="num">投资损益及未解释</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="r in data.explain" :key="r.from + r.to">
                  <td class="period">{{ r.from }} → {{ r.to }}</td>
                  <td class="num" :class="r.delta_net >= 0 ? 'pos' : 'neg'">{{ fmtSigned(r.delta_net) }}</td>
                  <td class="num">{{ r.income == null ? '—' : '¥' + fmt(r.income) }}</td>
                  <td class="num">{{ r.expense == null ? '—' : '¥' + fmt(r.expense) }}</td>
                  <td class="num">{{ fmtSigned(r.transfer_net) }}</td>
                  <td class="num">{{ r.refund_reimburse == null ? '—' : '¥' + fmt(r.refund_reimburse) }}</td>
                  <td class="num" :class="{ warn: r.residual != null && Math.abs(r.residual) >= 500 }">
                    {{ r.residual == null ? '—' : fmtSigned(r.residual) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p class="table-note">最后一列 = Δ净资产 − 流水可解释部分，包含投资涨跌、现金收支与漏记账；长期偏大说明有账外资金流动。</p>
        </template>
      </div>

      <!-- 账户管理 -->
      <div class="card accounts-card">
        <h3 class="card-title"><i class="fas fa-wallet"></i> 账户管理（{{ data.accounts.length }}）</h3>
        <div class="acc-list">
          <div v-for="acc in data.accounts" :key="acc.id" class="acc-item">
            <span class="acc-label">{{ acc.name }}</span>
            <button class="icon-btn" title="改名" @click="renameAccount(acc)"><i class="fas fa-pen"></i></button>
            <span class="type-badge" :class="{ liab: isLiability(acc) }">{{ acc.type }}</span>
            <span class="acc-balance" :class="{ liab: isLiability(acc) }">
              <template v-if="latestBalance(acc.id) != null">{{ isLiability(acc) ? '欠 ' : '' }}¥{{ fmt(latestBalance(acc.id)) }}</template>
              <template v-else>—</template>
            </span>
            <button class="icon-btn danger" title="删除账户" @click="deleteAccount(acc)"><i class="fas fa-trash"></i></button>
          </div>
        </div>
        <div class="add-row">
          <input v-model.trim="newAccName" class="text-input" placeholder="新账户名称" @keyup.enter="addAccount" />
          <select v-model="newAccType" class="select-input">
            <option v-for="t in data.account_types" :key="t" :value="t">{{ t }}</option>
          </select>
          <button class="primary-btn small" :disabled="!newAccName || adding" @click="addAccount">添加</button>
        </div>
      </div>

      <!-- 历史快照 -->
      <div class="card snaps-card">
        <h3 class="card-title"><i class="fas fa-clock-rotate-left"></i> 历史快照（{{ data.snapshots.length }}）</h3>
        <div v-if="!data.snapshots.length" class="card-empty">还没有快照，点右上角「+ 记一笔快照」开始记录。</div>
        <div v-else class="snap-list">
          <div v-for="s in sortedSnaps" :key="s.date" class="snap-item">
            <span class="snap-date">{{ s.date }}</span>
            <span class="snap-net">净资产 <b>{{ netOf(s.date) == null ? '—' : '¥' + fmt(netOf(s.date)) }}</b></span>
            <span class="snap-count">{{ Object.keys(s.balances || {}).length }} 个账户</span>
            <span class="snap-note">{{ s.note || '' }}</span>
            <button class="icon-btn danger" title="删除快照" @click="deleteSnapshot(s)"><i class="fas fa-trash"></i></button>
          </div>
        </div>
      </div>
    </template>
    </div><!-- /v-show sheet -->
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as echarts from 'echarts'
import api from '@/api/client'
import { useUiStore } from '@/stores/ui'
import IncomeView from './Income.vue'

const ui = useUiStore()

// 子页签:sheet=资产负债表 / income=收入分析(URL ?tab= 同步,可直链)
const route = useRoute()
const router = useRouter()
const tab = ref(route.query.tab === 'income' ? 'income' : 'sheet')
watch(tab, async (v) => {
  if (route.query.tab !== v) router.replace({ path: '/networth', query: v === 'sheet' ? {} : { tab: v } })
  if (v === 'sheet') { await nextTick(); resize() }   // 隐藏期 init 的图表尺寸为 0,回来补一次
})
watch(() => route.query.tab, (v) => {
  const want = v === 'income' ? 'income' : 'sheet'
  if (want !== tab.value) tab.value = want
})

const loading = ref(true)
const error = ref('')
const data = ref(null)

const showForm = ref(false)
const saving = ref(false)
const form = reactive({ date: '', note: '', balances: {} })

const newAccName = ref('')
const newAccType = ref('')
const adding = ref(false)

const trendRef = ref(null)
const pieRef = ref(null)
let trendChart = null
let pieChart = null

const PIE_COLORS = ['#34C759', '#30B0C7', '#007AFF', '#5856D6', '#FF9500', '#AF52DE', '#FFCC00', '#8E8E93']

const fmt = (v) => (v == null ? '—' : Number(v).toLocaleString('zh-CN', { maximumFractionDigits: 2 }))
const fmtSigned = (v) => (v == null ? '—' : (Number(v) > 0 ? '+' : '') + '¥' + fmt(v))
const fmtWan = (v) => {
  const n = Number(v || 0)
  return Math.abs(n) >= 10000 ? (n / 10000).toFixed(2) + '万' : fmt(n)
}

const latest = computed(() => {
  const t = data.value?.trend
  return t && t.length ? t[t.length - 1] : null
})

// 最新一次快照（按日期取最大）
const latestSnap = computed(() => {
  const s = data.value?.snapshots
  if (!s || !s.length) return null
  return [...s].sort((a, b) => (a.date < b.date ? 1 : -1))[0]
})

const sortedSnaps = computed(() => {
  const s = data.value?.snapshots || []
  return [...s].sort((a, b) => (a.date < b.date ? 1 : -1))
})

// 最新一期 by_type 里金额为负的 = 负债类
const latestLiabs = computed(() => {
  if (!latest.value) return []
  return Object.entries(latest.value.by_type || {})
    .filter(([, v]) => v < 0)
    .map(([type, v]) => ({ type, amount: -v }))
})

const isLiability = (acc) => (data.value?.liability_types || []).includes(acc.type)
const latestBalance = (aid) => {
  const b = latestSnap.value?.balances
  return b && b[aid] != null ? b[aid] : null
}
const netOf = (date) => {
  const p = (data.value?.trend || []).find((x) => x.date === date)
  return p ? p.net : null
}

function localToday() {
  const d = new Date()
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

function toggleForm() {
  if (showForm.value) { showForm.value = false; return }
  form.date = localToday()
  form.note = ''
  form.balances = {}
  for (const acc of data.value.accounts) {
    const last = latestBalance(acc.id)
    form.balances[acc.id] = last != null ? last : ''
  }
  showForm.value = true
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await api.networthGet()
    if (!newAccType.value && data.value.account_types?.length) newAccType.value = data.value.account_types[0]
    loading.value = false   // 必须先揭开 v-else 模板,图表容器才存在
    await nextTick()
    renderCharts()
  } catch (e) {
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

// 写操作统一刷新：接口返回最新总览
async function refreshWith(overview) {
  data.value = overview
  await nextTick()
  renderCharts()
}

async function saveSnapshot() {
  if (!form.date) { ui.showError('请选择快照日期'); return }
  const balances = {}
  for (const acc of data.value.accounts) {
    const v = form.balances[acc.id]
    if (v !== '' && v != null && !Number.isNaN(Number(v))) balances[acc.id] = Number(v)
  }
  if (!Object.keys(balances).length) { ui.showError('至少填写一个账户余额'); return }
  saving.value = true
  try {
    const overview = await api.networthSaveSnapshot(form.date, balances, form.note || '')
    await refreshWith(overview)
    showForm.value = false
    ui.showSuccess('快照已记录')
  } catch (e) {
    ui.showError(e.message)
  } finally {
    saving.value = false
  }
}

async function addAccount() {
  if (!newAccName.value) return
  adding.value = true
  try {
    const overview = await api.networthAddAccount(newAccName.value, newAccType.value)
    await refreshWith(overview)
    newAccName.value = ''
    ui.showSuccess('账户已添加')
  } catch (e) {
    ui.showError(e.message)
  } finally {
    adding.value = false
  }
}

async function renameAccount(acc) {
  const name = prompt('修改账户名称', acc.name)
  if (!name || !name.trim() || name.trim() === acc.name) return
  try {
    const overview = await api.networthUpdateAccount(acc.id, { name: name.trim() })
    await refreshWith(overview)
    ui.showSuccess('账户已改名')
  } catch (e) {
    ui.showError(e.message)
  }
}

async function deleteAccount(acc) {
  if (!confirm(`确定删除账户「${acc.name}」？该账户会同时从所有历史快照中移除，历史净资产将重新计算。`)) return
  try {
    const overview = await api.networthDeleteAccount(acc.id)
    await refreshWith(overview)
    ui.showSuccess('账户已删除')
  } catch (e) {
    ui.showError(e.message)
  }
}

async function deleteSnapshot(s) {
  if (!confirm(`确定删除 ${s.date} 的快照？`)) return
  try {
    const overview = await api.networthDeleteSnapshot(s.date)
    await refreshWith(overview)
    ui.showSuccess('快照已删除')
  } catch (e) {
    ui.showError(e.message)
  }
}

function renderCharts() {
  const t = data.value?.trend
  if (!t || !t.length) return

  // 净资产趋势折线
  if (trendRef.value) {
    if (trendChart && trendChart.getDom() !== trendRef.value) { trendChart.dispose(); trendChart = null }
    trendChart = trendChart || echarts.init(trendRef.value)
    trendChart.setOption({
      tooltip: { trigger: 'axis', valueFormatter: (v) => '¥' + fmt(v) },
      legend: { top: 0, textStyle: { fontSize: 11 } },
      grid: { left: 56, right: 16, top: 32, bottom: 28 },
      xAxis: { type: 'category', boundaryGap: false, data: t.map((p) => p.date), axisLabel: { fontSize: 10 } },
      yAxis: { type: 'value', scale: true, axisLabel: { formatter: (v) => fmtWan(v) } },
      series: [
        {
          name: '净资产', type: 'line', data: t.map((p) => p.net),
          symbolSize: 6, lineStyle: { color: '#34C759', width: 3 },
          itemStyle: { color: '#34C759' },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(52, 199, 89, 0.25)' },
              { offset: 1, color: 'rgba(52, 199, 89, 0.02)' },
            ]),
          },
        },
        {
          name: '总资产', type: 'line', data: t.map((p) => p.assets),
          symbol: 'none', lineStyle: { color: '#86E3A4', width: 1.5, type: 'dashed' },
          itemStyle: { color: '#86E3A4' },
        },
        {
          name: '总负债', type: 'line', data: t.map((p) => p.liabilities),
          symbol: 'none', lineStyle: { color: '#FF9F9A', width: 1.5, type: 'dashed' },
          itemStyle: { color: '#FF9F9A' },
        },
      ],
    })
  }

  // 最新资产构成饼图（只取金额>0 的资产类）
  if (pieRef.value && latest.value) {
    const items = Object.entries(latest.value.by_type || {})
      .filter(([, v]) => v > 0)
      .map(([type, v], i) => ({ name: type, value: Number(v.toFixed ? v.toFixed(2) : v), itemStyle: { color: PIE_COLORS[i % PIE_COLORS.length] } }))
    if (pieChart && pieChart.getDom() !== pieRef.value) { pieChart.dispose(); pieChart = null }
    pieChart = pieChart || echarts.init(pieRef.value)
    pieChart.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: ¥{c} ({d}%)' },
      legend: { bottom: 0, type: 'scroll', textStyle: { fontSize: 11 } },
      series: [{
        type: 'pie', radius: ['42%', '68%'], center: ['50%', '44%'], avoidLabelOverlap: true,
        itemStyle: { borderColor: '#fff', borderWidth: 2, borderRadius: 4 },
        label: { formatter: '{b}\n{d}%', fontSize: 11 },
        data: items,
      }],
    })
  }
}

function resize() {
  trendChart && trendChart.resize()
  pieChart && pieChart.resize()
}

onMounted(() => {
  load()
  window.addEventListener('resize', resize)
})
onUnmounted(() => {
  window.removeEventListener('resize', resize)
  trendChart && trendChart.dispose()
  pieChart && pieChart.dispose()
})
</script>

<style scoped>
.networth-page { max-width: 1200px; margin: 0 auto; }

/* 子页签 */
.header-right { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.nw-tabs {
  display: flex; gap: 4px; background: var(--card-bg, #fff);
  border: 1px solid var(--border-color, #ecedf1); border-radius: 12px; padding: 4px;
}
.nw-tab {
  display: inline-flex; align-items: center; gap: 7px; height: 36px; padding: 0 16px;
  border: none; background: none; color: #5a5a60; font-size: 13.5px; font-weight: 500;
  border-radius: 9px; cursor: pointer; transition: all .15s;
}
.nw-tab i { font-size: 13px; opacity: .85; }
.nw-tab:hover { background: #f3f5f9; color: #34C759; }
.nw-tab.active { background: #34C759; color: #fff; box-shadow: 0 4px 12px rgba(52,199,89,.22); }

.page-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  gap: 16px; margin-bottom: 20px; flex-wrap: wrap;
}
.page-title { font-size: 24px; font-weight: 600; color: var(--text-color); margin: 0 0 6px; }
.page-sub { font-size: 13px; color: var(--text-secondary, #8E8E93); margin: 0; max-width: 640px; line-height: 1.5; }

.state-box { padding: 60px 0; text-align: center; color: var(--text-secondary, #8E8E93); }
.state-box.error { color: #FF3B30; }

/* 按钮 */
.primary-btn {
  padding: 9px 18px; background: #34C759; color: #fff; border: none;
  border-radius: var(--radius-md); font-size: 14px; font-weight: 600; cursor: pointer;
  display: inline-flex; align-items: center; gap: 7px; transition: opacity .2s; flex-shrink: 0;
}
.primary-btn:hover:not(:disabled) { opacity: .85; }
.primary-btn:disabled { opacity: .45; cursor: not-allowed; }
.primary-btn.small { padding: 8px 16px; font-size: 13px; }
.ghost-btn {
  padding: 9px 18px; background: var(--card-bg); color: var(--text-color);
  border: 1px solid var(--border-color); border-radius: var(--radius-md);
  font-size: 14px; cursor: pointer; transition: all .2s;
}
.ghost-btn:hover { background: var(--hover-bg, #F2F2F7); }
.icon-btn {
  width: 28px; height: 28px; border: none; background: transparent; border-radius: 7px;
  color: var(--text-secondary, #8E8E93); cursor: pointer; font-size: 12px; flex-shrink: 0;
  transition: all .2s;
}
.icon-btn:hover { background: var(--hover-bg, #F2F2F7); color: var(--text-color); }
.icon-btn.danger:hover { background: #FF3B3014; color: #FF3B30; }

/* 卡片 */
.card {
  background: var(--card-bg); border: 1px solid var(--border-color);
  border-radius: var(--radius-md); padding: 18px; margin-bottom: 18px;
}
.card-title { font-size: 15px; font-weight: 600; color: var(--text-color); margin: 0 0 14px; display: flex; align-items: center; gap: 8px; }
.card-title i { color: #34C759; font-size: 14px; }
.card-empty { padding: 26px 0; text-align: center; font-size: 13px; color: var(--text-secondary, #8E8E93); }

/* 空状态引导 */
.empty-card { text-align: center; padding: 40px 24px; }
.empty-icon { font-size: 34px; color: #34C759; margin-bottom: 12px; }
.empty-title { font-size: 17px; font-weight: 600; color: var(--text-color); margin: 0 0 18px; }
.empty-steps {
  display: flex; align-items: center; justify-content: center; gap: 12px;
  flex-wrap: wrap; margin-bottom: 24px;
}
.empty-step {
  font-size: 13px; color: var(--text-color); background: var(--hover-bg, #F2F2F7);
  padding: 10px 14px; border-radius: var(--radius-md);
}
.step-no { color: #34C759; font-weight: 700; margin-right: 4px; }
.step-arrow { color: var(--text-secondary, #8E8E93); font-size: 12px; }

/* KPI */
.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 18px; }
.kpi-card {
  background: var(--card-bg); border: 1px solid var(--border-color); border-radius: var(--radius-md);
  padding: 16px; display: flex; align-items: center; gap: 12px;
}
.kpi-icon { width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0; }
.kpi-num { font-size: 20px; font-weight: 600; color: var(--text-color); line-height: 1.2; }
.kpi-num.big { font-size: 22px; font-weight: 700; }
.kpi-num.green { color: #34C759; }
.kpi-num.red { color: #FF3B30; }
.kpi-label { font-size: 12px; color: var(--text-secondary, #8E8E93); }

/* 输入控件 */
.text-input, .select-input, .num-input {
  padding: 9px 12px; border: 1px solid var(--border-color); border-radius: 8px;
  background: var(--card-bg); color: var(--text-color); font-size: 13px; outline: none;
  transition: border-color .2s;
}
.text-input:focus, .select-input:focus, .num-input:focus { border-color: #34C759; }

/* 快照表单 */
.form-meta { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; flex-wrap: wrap; }
.form-label { font-size: 13px; font-weight: 600; color: var(--text-color); flex-shrink: 0; }
.form-hint { font-size: 12px; color: var(--text-secondary, #8E8E93); }
.note-input { flex: 1; min-width: 200px; }
.snap-accounts {
  display: grid; grid-template-columns: 1fr 1fr; gap: 10px 20px;
  padding: 14px; background: var(--hover-bg, #F2F2F7); border-radius: var(--radius-md);
  margin-bottom: 14px;
}
.acc-row { display: flex; align-items: center; gap: 10px; }
.acc-name { flex: 1; min-width: 0; display: flex; align-items: center; gap: 8px; }
.acc-label { font-size: 13px; font-weight: 500; color: var(--text-color); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.acc-input-wrap { position: relative; flex-shrink: 0; }
.num-input { width: 150px; text-align: right; }
.num-input.liab-input { border-color: #FF3B30; padding-right: 44px; }
.liab-tag {
  position: absolute; right: 10px; top: 50%; transform: translateY(-50%);
  font-size: 11px; color: #FF3B30; font-weight: 600; pointer-events: none;
}
.form-actions { display: flex; gap: 10px; }

/* 类型徽标 */
.type-badge {
  display: inline-block; padding: 1px 8px; border-radius: 10px; font-size: 11px; font-weight: 500;
  color: #34C759; background: #34C7591A; border: 1px solid #34C75955; flex-shrink: 0;
}
.type-badge.liab { color: #FF3B30; background: #FF3B301A; border-color: #FF3B3055; }

/* 图表 */
.charts-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 18px; }
.chart-card { margin-bottom: 0; }
.chart { width: 100%; height: 300px; }
.pie-liabs { display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; margin-top: 8px; }
.pie-liab { font-size: 12px; padding: 2px 10px; border-radius: 10px; background: #FF3B3014; color: #FF3B30; }

/* 解释表格 */
.table-wrap { overflow-x: auto; }
.explain-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.explain-table th {
  text-align: left; font-weight: 600; color: var(--text-secondary, #8E8E93); font-size: 12px;
  padding: 8px 10px; border-bottom: 1px solid var(--border-color); white-space: nowrap;
}
.explain-table td { padding: 9px 10px; border-bottom: 1px solid var(--border-color); color: var(--text-color); white-space: nowrap; }
.explain-table tr:last-child td { border-bottom: none; }
.explain-table th.num, .explain-table td.num { text-align: right; }
.explain-table .period { font-variant-numeric: tabular-nums; }
.explain-table .pos { color: #34C759; font-weight: 600; }
.explain-table .neg { color: #FF3B30; font-weight: 600; }
.explain-table .warn { color: #FF9500; font-weight: 600; }
.table-note { font-size: 12px; color: var(--text-secondary, #8E8E93); margin: 12px 0 0; line-height: 1.5; }

/* 账户管理 */
.acc-list { margin-bottom: 14px; }
.acc-item {
  display: flex; align-items: center; gap: 10px; padding: 10px 4px;
  border-bottom: 1px solid var(--border-color);
}
.acc-item:last-child { border-bottom: none; }
.acc-item .acc-label { flex: 0 1 auto; }
.acc-balance { margin-left: auto; font-size: 13px; font-weight: 600; color: var(--text-color); font-variant-numeric: tabular-nums; }
.acc-balance.liab { color: #FF3B30; }
.add-row { display: flex; gap: 10px; flex-wrap: wrap; justify-content: center; }
.add-row .text-input { flex: 1; min-width: 180px; max-width: 320px; }

/* 历史快照 */
.snap-item {
  display: flex; align-items: center; gap: 14px; padding: 10px 4px;
  border-bottom: 1px solid var(--border-color); font-size: 13px;
}
.snap-item:last-child { border-bottom: none; }
.snap-date { font-weight: 600; color: var(--text-color); font-variant-numeric: tabular-nums; flex-shrink: 0; }
.snap-net { color: var(--text-secondary, #8E8E93); flex-shrink: 0; }
.snap-net b { color: #34C759; }
.snap-count { color: var(--text-secondary, #8E8E93); flex-shrink: 0; }
.snap-note { flex: 1; min-width: 0; color: var(--text-secondary, #8E8E93); font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

@media (max-width: 1000px) {
  .kpi-row { grid-template-columns: repeat(2, 1fr); }
  .charts-grid { grid-template-columns: 1fr; }
  .snap-accounts { grid-template-columns: 1fr; }
  .snap-item { flex-wrap: wrap; gap: 8px; }
}
</style>
