<template>
  <div class="home-page">
    <!-- 顶部问候 -->
    <div class="home-head">
      <div>
        <h1 class="home-title">{{ greeting }}，{{ authStore.displayName || '欢迎回来' }}</h1>
        <p class="home-sub">
          {{ today }}
          <template v-if="data && !data.empty && data.date_range">
            · 账单覆盖 {{ data.date_range[0] }} ~ {{ data.date_range[1] }}，共 {{ data.total_count.toLocaleString() }} 笔
          </template>
        </p>
      </div>
    </div>

    <div v-if="loading" class="state-box">加载中…</div>

    <!-- 空态:引导上传 -->
    <div v-else-if="!data || data.empty" class="empty-card">
      <div class="empty-icon"><i class="fas fa-wallet"></i></div>
      <h3>还没有账单数据</h3>
      <p>上传支付宝/微信/银行账单，或从邮箱一键导入，立刻得到消费、收入、资产的全景分析。</p>
      <div class="empty-actions">
        <router-link to="/settings" class="btn-primary"><i class="fas fa-upload"></i> 上传 / 邮箱导入账单</router-link>
        <button class="btn-ghost" @click="enterDemoMode"><i class="fas fa-eye"></i> 查看示例数据</button>
      </div>
    </div>

    <!-- 仪表盘 + 对话 -->
    <template v-else>
      <!-- KPI -->
      <div class="kpi-row">
        <div class="kpi-card">
          <div class="kpi-top"><span class="kpi-label">本月消费</span>
            <span v-if="data.mom_pct != null" class="kpi-tag" :class="data.mom_pct > 0 ? 'up' : 'down'">
              <i :class="data.mom_pct > 0 ? 'fas fa-arrow-up' : 'fas fa-arrow-down'"></i> {{ Math.abs(data.mom_pct) }}%
            </span>
          </div>
          <div class="kpi-num">¥{{ fmt(data.this_month_expense) }}</div>
          <div class="kpi-foot">上月 ¥{{ fmt(data.last_month_expense) }}</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-top"><span class="kpi-label">今年真实消费</span></div>
          <div class="kpi-num red">¥{{ fmt(data.year_expense) }}</div>
          <div class="kpi-foot">已剔除转账/还款/投资</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-top"><span class="kpi-label">今年真实收入</span></div>
          <div class="kpi-num green">¥{{ fmt(data.year_income) }}</div>
          <div class="kpi-foot">工资+理财+其他</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-top"><span class="kpi-label">{{ data.net_worth ? '净资产' : '今年结余' }}</span></div>
          <div class="kpi-num" :class="netClass">¥{{ fmt(data.net_worth ? data.net_worth.net : data.year_balance) }}</div>
          <div class="kpi-foot">
            <template v-if="data.net_worth">截至 {{ data.net_worth.date }}</template>
            <router-link v-else to="/networth" class="kpi-link">记一笔资产快照 →</router-link>
          </div>
        </div>
      </div>

      <div class="dash-grid">
        <!-- 左:仪表盘卡片 -->
        <div class="dash-left">
          <!-- 预算 -->
          <div class="card">
            <div class="card-head">
              <h3><i class="fas fa-bullseye" style="color:#FF9500"></i> 本月预算</h3>
              <button class="mini-link" @click="openBudget"><i class="fas fa-pen"></i> {{ budgetSet ? '编辑' : '设置' }}</button>
            </div>
            <template v-if="budget && budget.has_budget">
              <div v-if="budget.total_budget" class="bud-total">
                <div class="bud-bar-row">
                  <div class="bud-bar"><div class="bud-fill" :class="{ over: budget.total_pct > 100 }" :style="{ width: Math.min(budget.total_pct, 100) + '%' }"></div></div>
                  <span class="bud-pct" :class="{ over: budget.total_pct > 100 }">{{ budget.total_pct }}%</span>
                </div>
                <div class="bud-line">
                  已花 <b>¥{{ fmt(budget.total_spent) }}</b> / ¥{{ fmt(budget.total_budget) }}
                  <span :class="budget.total_remaining < 0 ? 'red' : 'green'">（{{ budget.total_remaining < 0 ? '超支' : '剩余' }} ¥{{ fmt(Math.abs(budget.total_remaining)) }}）</span>
                </div>
                <div class="bud-proj" :class="{ warn: budget.projected_over }">
                  <i :class="budget.projected_over ? 'fas fa-triangle-exclamation' : 'fas fa-gauge'"></i>
                  按当前节奏预计月末 <b>¥{{ fmt(budget.projected) }}</b>{{ budget.projected_over ? '，将超预算' : '' }}
                </div>
              </div>
              <div v-if="budget.categories && budget.categories.length" class="bud-cats">
                <div v-for="c in budget.categories" :key="c.category" class="bud-cat">
                  <div class="bud-cat-head"><span>{{ c.category }}</span><span :class="{ red: c.over }">¥{{ fmt(c.spent) }} / {{ fmt(c.budget) }}</span></div>
                  <div class="bud-bar sm"><div class="bud-fill" :class="{ over: c.over }" :style="{ width: Math.min(c.pct || 0, 100) + '%' }"></div></div>
                </div>
              </div>
            </template>
            <div v-else class="card-empty">
              还没设预算。设一个月度总额(和可选的分类预算)，首页就能盯着进度，月底不超支。
            </div>
          </div>

          <!-- 近6月趋势 -->
          <div class="card">
            <div class="card-head"><h3><i class="fas fa-chart-column" style="color:#5856D6"></i> 近 6 个月消费</h3></div>
            <div ref="trendRef" class="mini-chart"></div>
          </div>

          <!-- 本月 top 分类 + 近期大额 -->
          <div class="card two-col">
            <div class="tc-block">
              <div class="card-head"><h3><i class="fas fa-tags" style="color:#FF9500"></i> 本月分类 Top</h3></div>
              <div v-if="!data.top_categories.length" class="card-empty sm">本月暂无消费</div>
              <div v-for="c in data.top_categories" :key="c.category" class="rank-row">
                <span class="rank-name">{{ c.category }}</span>
                <span class="rank-amt">¥{{ fmt(c.amount) }}</span>
              </div>
            </div>
            <div class="tc-block">
              <div class="card-head"><h3><i class="fas fa-fire" style="color:#FF3B30"></i> 近期大额</h3></div>
              <div v-if="!data.recent_large.length" class="card-empty sm">今年暂无 ≥1000 元支出</div>
              <div v-for="(r, i) in data.recent_large" :key="i" class="large-row">
                <div class="large-main"><span class="large-amt">¥{{ fmt(r.amount) }}</span> <span class="large-cat">{{ r.category }}</span></div>
                <div class="large-sub">{{ r.time }} · {{ r.desc || r.counterparty || '—' }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 右:AI 对话 -->
        <div class="dash-right">
          <div class="card chat-card">
            <div class="card-head">
              <h3><i class="fas fa-robot" style="color:#AF52DE"></i> AI 助手</h3>
              <router-link to="/ai" class="mini-link">完整版 <i class="fas fa-up-right-from-square"></i></router-link>
            </div>
            <MiniChat />
          </div>
        </div>
      </div>
    </template>

    <!-- 预算编辑弹窗 -->
    <teleport to="body">
      <div v-if="budgetModal" class="modal-mask" @click.self="budgetModal = false">
        <div class="modal-card">
          <div class="modal-head"><h3>设置月度预算</h3><button class="modal-x" @click="budgetModal = false">×</button></div>
          <div class="modal-body">
            <div class="field">
              <label>月度总预算（元）</label>
              <input v-model.number="bform.total" type="number" min="0" placeholder="如 8000，留空表示不设总额" />
            </div>
            <div class="field">
              <label>分类预算（可选）</label>
              <div v-for="(c, i) in bform.cats" :key="i" class="cat-edit-row">
                <input v-model.trim="c.name" list="home-cat-list" placeholder="分类名" />
                <input v-model.number="c.amount" type="number" min="0" placeholder="额度" />
                <button class="row-del" @click="bform.cats.splice(i, 1)">×</button>
              </div>
              <datalist id="home-cat-list">
                <option v-for="c in (budget && budget.top_categories || []).map(x => x.category)" :key="c" :value="c" />
                <option v-for="c in data.top_categories.map(x => x.category)" :key="'t' + c" :value="c" />
              </datalist>
              <button class="add-cat" @click="bform.cats.push({ name: '', amount: null })"><i class="fas fa-plus"></i> 加一个分类预算</button>
            </div>
          </div>
          <div class="modal-foot">
            <button class="btn-ghost" @click="budgetModal = false">取消</button>
            <button class="btn-primary" :disabled="budgetSaving" @click="saveBudget">保存</button>
          </div>
        </div>
      </div>
    </teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import api from '@/api/client'
import { useUiStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'
import { useSessionStore } from '@/stores/session'
import MiniChat from '@/components/MiniChat.vue'

const router = useRouter()
const uiStore = useUiStore()
const authStore = useAuthStore()
const sessionStore = useSessionStore()

const loading = ref(true)
const data = ref(null)
const budget = ref(null)
const trendRef = ref(null)
let trendChart = null

const budgetModal = ref(false)
const budgetSaving = ref(false)
const bform = ref({ total: null, cats: [] })

const today = new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })
const greeting = computed(() => {
  const h = new Date().getHours()
  return h < 6 ? '夜深了' : h < 11 ? '早上好' : h < 13 ? '中午好' : h < 18 ? '下午好' : '晚上好'
})
const budgetSet = computed(() => budget.value && budget.value.has_budget)
const netClass = computed(() => {
  const v = data.value && (data.value.net_worth ? data.value.net_worth.net : data.value.year_balance)
  return v < 0 ? 'red' : ''
})

function fmt(v) {
  return v == null ? '0' : Number(v).toLocaleString('zh-CN', { maximumFractionDigits: 0 })
}

async function load() {
  loading.value = true
  try {
    const r = await api.homeOverview()
    data.value = r
    budget.value = r.budget || null
    if (!r.empty) {
      loading.value = false
      await nextTick()
      renderTrend()
    }
  } catch (e) {
    uiStore.showError('加载失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

function renderTrend() {
  if (!trendRef.value || !data.value || !data.value.monthly_trend) return
  if (trendChart && trendChart.getDom() !== trendRef.value) { trendChart.dispose(); trendChart = null }
  trendChart = trendChart || echarts.init(trendRef.value)
  const t = data.value.monthly_trend
  trendChart.setOption({
    grid: { left: 50, right: 12, top: 16, bottom: 24 },
    tooltip: { trigger: 'axis', valueFormatter: (v) => '¥' + fmt(v) },
    xAxis: { type: 'category', data: t.map(x => x.month.slice(5)), axisLabel: { fontSize: 11 } },
    yAxis: { type: 'value', axisLabel: { formatter: (v) => v >= 10000 ? (v / 10000) + '万' : v, fontSize: 10 } },
    series: [{
      type: 'bar', data: t.map(x => x.amount), barWidth: '52%',
      itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: '#7B61FF' }, { offset: 1, color: '#AF52DE' }]), borderRadius: [6, 6, 0, 0] },
    }],
  })
  trendChart.resize()
}

function openBudget() {
  const b = budget.value
  bform.value = {
    total: b && b.total_budget ? b.total_budget : null,
    cats: b && b.categories ? b.categories.map(c => ({ name: c.category, amount: c.budget })) : [],
  }
  budgetModal.value = true
}

async function saveBudget() {
  budgetSaving.value = true
  try {
    const cats = {}
    for (const c of bform.value.cats) {
      if (c.name && c.amount > 0) cats[c.name] = c.amount
    }
    await api.budgetSave({ monthly_total: bform.value.total || null, categories: cats })
    budgetModal.value = false
    uiStore.showSuccess('预算已保存')
    const st = await api.budgetStatus({})
    budget.value = st.status && st.status.has_budget ? st.status : null
  } catch (e) {
    uiStore.showError('保存失败: ' + e.message)
  } finally {
    budgetSaving.value = false
  }
}

async function enterDemoMode() {
  try {
    await sessionStore.enterDemoMode()
    uiStore.showSuccess('已进入演示模式')
    location.href = '/'
  } catch (e) { uiStore.showError('进入演示模式失败: ' + e.message) }
}

function onResize() { trendChart && trendChart.resize() }
onMounted(() => { load(); window.addEventListener('resize', onResize) })
onUnmounted(() => { window.removeEventListener('resize', onResize); trendChart && trendChart.dispose() })
</script>

<style scoped>
.home-page { max-width: 1320px; margin: 0 auto; }
.home-head { margin-bottom: 18px; }
.home-title { font-size: 24px; font-weight: 600; color: var(--text-color); margin: 0; }
.home-sub { font-size: 13px; color: var(--text-secondary, #8a8a8f); margin: 6px 0 0; }
.state-box { padding: 60px 0; text-align: center; color: #8a8a8f; }

/* 空态 */
.empty-card { background: var(--card-bg, #fff); border: 1px solid var(--border-color, #ececf2); border-radius: 18px; padding: 48px 24px; text-align: center; }
.empty-icon { width: 64px; height: 64px; margin: 0 auto 16px; border-radius: 18px; background: rgba(0,122,255,.1); color: #007AFF; display: flex; align-items: center; justify-content: center; font-size: 28px; }
.empty-card h3 { font-size: 19px; color: #1d1d1f; margin: 0 0 8px; }
.empty-card p { font-size: 14px; color: #8a8a8f; max-width: 520px; margin: 0 auto 22px; line-height: 1.6; }
.empty-actions { display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; }

/* KPI */
.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 14px; }
@media (max-width: 900px) { .kpi-row { grid-template-columns: repeat(2, 1fr); } }
.kpi-card { background: var(--card-bg, #fff); border: 1px solid var(--border-color, #ececf2); border-radius: 16px; padding: 16px 18px; }
.kpi-top { display: flex; align-items: center; justify-content: space-between; }
.kpi-label { font-size: 13px; color: #8a8a8f; }
.kpi-tag { font-size: 11px; border-radius: 7px; padding: 1px 7px; }
.kpi-tag.up { background: #feeeec; color: #d04437; }
.kpi-tag.down { background: #e6f6ec; color: #1d8a44; }
.kpi-num { font-size: 26px; font-weight: 650; color: #1d1d1f; margin: 6px 0 2px; letter-spacing: -.5px; }
.kpi-num.red { color: #FF3B30; }
.kpi-num.green { color: #34C759; }
.kpi-foot { font-size: 12px; color: #a0a0a6; }
.kpi-link { color: #007AFF; text-decoration: none; }

/* 仪表盘网格 */
.dash-grid { display: grid; grid-template-columns: 1.05fr .95fr; gap: 14px; align-items: start; }
@media (max-width: 1000px) { .dash-grid { grid-template-columns: 1fr; } }
.dash-left { display: flex; flex-direction: column; gap: 14px; }

.card { background: var(--card-bg, #fff); border: 1px solid var(--border-color, #ececf2); border-radius: 16px; padding: 16px 18px; }
.card-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.card-head h3 { font-size: 15px; font-weight: 600; color: #1d1d1f; margin: 0; display: flex; align-items: center; gap: 8px; }
.mini-link { font-size: 12.5px; color: #007AFF; text-decoration: none; cursor: pointer; background: none; border: none; }
.card-empty { font-size: 13px; color: #9a9aa0; line-height: 1.6; padding: 4px 0; }
.card-empty.sm { font-size: 12.5px; padding: 8px 0; }

/* 预算 */
.bud-bar-row { display: flex; align-items: center; gap: 10px; }
.bud-bar { flex: 1; height: 10px; background: #f0f0f4; border-radius: 6px; overflow: hidden; }
.bud-bar.sm { height: 7px; }
.bud-fill { height: 100%; background: linear-gradient(90deg, #34C759, #30b350); border-radius: 6px; transition: width .4s; }
.bud-fill.over { background: linear-gradient(90deg, #FF9500, #FF3B30); }
.bud-pct { font-size: 13px; font-weight: 600; color: #34C759; min-width: 42px; text-align: right; }
.bud-pct.over { color: #FF3B30; }
.bud-line { font-size: 13px; color: #4a4a4f; margin-top: 9px; }
.bud-proj { font-size: 12.5px; color: #8a8a8f; margin-top: 7px; display: flex; align-items: center; gap: 6px; }
.bud-proj.warn { color: #d04437; }
.bud-cats { margin-top: 14px; display: flex; flex-direction: column; gap: 10px; border-top: 1px solid #f3f3f6; padding-top: 12px; }
.bud-cat-head { display: flex; justify-content: space-between; font-size: 12.5px; color: #4a4a4f; margin-bottom: 5px; }

.mini-chart { width: 100%; height: 180px; }

/* top 分类 / 大额 */
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
@media (max-width: 560px) { .two-col { grid-template-columns: 1fr; } }
.rank-row { display: flex; justify-content: space-between; font-size: 13px; padding: 6px 0; border-bottom: 1px solid #f5f5f8; }
.rank-row:last-child { border-bottom: none; }
.rank-name { color: #4a4a4f; }
.rank-amt { color: #1d1d1f; font-weight: 600; font-variant-numeric: tabular-nums; }
.large-row { padding: 7px 0; border-bottom: 1px solid #f5f5f8; }
.large-row:last-child { border-bottom: none; }
.large-amt { font-weight: 650; color: #FF3B30; }
.large-cat { font-size: 12px; color: #8a8a8f; }
.large-sub { font-size: 12px; color: #a0a0a6; margin-top: 2px; }

/* 对话 */
.chat-card { display: flex; flex-direction: column; height: 620px; position: sticky; top: 12px; }
.chat-card :deep(.mini-chat) { flex: 1; min-height: 0; }

.red { color: #FF3B30; }
.green { color: #34C759; }

/* 通用按钮 */
.btn-primary { display: inline-flex; align-items: center; gap: 8px; height: 42px; padding: 0 20px; background: #007AFF; color: #fff; border: none; border-radius: 11px; font-size: 14px; cursor: pointer; text-decoration: none; }
.btn-primary:hover { background: #0a6ee0; }
.btn-primary:disabled { opacity: .6; }
.btn-ghost { display: inline-flex; align-items: center; gap: 8px; height: 42px; padding: 0 20px; background: #fff; color: #4a4a4f; border: 1px solid #e2e2e8; border-radius: 11px; font-size: 14px; cursor: pointer; }
.btn-ghost:hover { border-color: #007AFF; color: #007AFF; }

/* 弹窗 */
.modal-mask { position: fixed; inset: 0; background: rgba(0,0,0,.4); display: flex; align-items: center; justify-content: center; z-index: 2000; padding: 16px; }
.modal-card { background: #fff; border-radius: 16px; width: 460px; max-width: 100%; max-height: 86vh; display: flex; flex-direction: column; overflow: hidden; }
.modal-head { display: flex; align-items: center; justify-content: space-between; padding: 16px 18px; border-bottom: 1px solid #f0f0f4; }
.modal-head h3 { margin: 0; font-size: 16px; }
.modal-x { border: none; background: none; font-size: 22px; color: #aaa; cursor: pointer; line-height: 1; }
.modal-body { padding: 18px; overflow-y: auto; }
.field { margin-bottom: 16px; }
.field > label { display: block; font-size: 13px; color: #4a4a4f; margin-bottom: 7px; }
.field input { width: 100%; height: 38px; border: 1px solid #e2e2e8; border-radius: 9px; padding: 0 12px; font-size: 14px; outline: none; box-sizing: border-box; }
.field input:focus { border-color: #007AFF; }
.cat-edit-row { display: flex; gap: 8px; margin-bottom: 8px; }
.cat-edit-row input:first-child { flex: 1.4; }
.cat-edit-row input:nth-child(2) { flex: 1; }
.row-del { width: 34px; flex-shrink: 0; border: 1px solid #eee; background: #fafafa; border-radius: 9px; color: #c0392b; cursor: pointer; font-size: 16px; }
.add-cat { margin-top: 4px; border: 1px dashed #c9d8ec; background: #f7fafe; color: #007AFF; border-radius: 9px; height: 36px; width: 100%; cursor: pointer; font-size: 13px; }
.modal-foot { display: flex; justify-content: flex-end; gap: 10px; padding: 14px 18px; border-top: 1px solid #f0f0f4; }
</style>
