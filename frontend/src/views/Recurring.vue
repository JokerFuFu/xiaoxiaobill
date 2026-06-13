<template>
  <div class="recurring-view">
    <div v-if="loading" class="state-box">识别中…</div>
    <div v-else-if="empty" class="state-box">还没有账单数据，先去上传。</div>
    <div v-else-if="!data.count" class="state-box">没有识别到明显的订阅或定期扣费。<br /><span class="muted">判定依据:同一对手方按月/季/年规律重复、金额稳定，或命中订阅关键词。</span></div>

    <template v-else>
      <!-- 汇总 -->
      <div class="sum-row">
        <div class="sum-card">
          <div class="sum-label">每月固定支出</div>
          <div class="sum-num">¥{{ fmt(data.monthly_total) }}</div>
          <div class="sum-foot">{{ data.count }} 项订阅/定期扣费</div>
        </div>
        <div class="sum-card">
          <div class="sum-label">折合每年</div>
          <div class="sum-num orange">¥{{ fmt(data.annual_total) }}</div>
          <div class="sum-foot">这些固定开销一年要花掉</div>
        </div>
        <div class="sum-card type-card">
          <div class="sum-label">按类型</div>
          <div class="type-chips">
            <span v-for="t in data.by_type" :key="t.type" class="type-chip" :style="{ borderColor: typeColor(t.type) }">
              <span class="dot" :style="{ background: typeColor(t.type) }"></span>{{ t.type }}
              <b>¥{{ fmt(t.monthly_cost) }}/月</b>
            </span>
          </div>
        </div>
      </div>

      <!-- 列表 -->
      <div class="card">
        <div class="card-head"><h3><i class="fas fa-repeat" style="color:#5856D6"></i> 识别到的订阅 / 定期扣费</h3>
          <span class="muted">按月成本排序</span></div>
        <div class="rec-list">
          <div v-for="(it, i) in data.items" :key="i" class="rec-row">
            <div class="rec-left">
              <span class="rec-badge" :style="{ background: typeColor(it.type) }">{{ it.type }}</span>
              <div class="rec-name">
                <span class="rec-merchant">{{ it.merchant }}</span>
                <span class="rec-sub">{{ it.cadence }} · 已扣 {{ it.count }} 笔 / {{ it.months }} 个月{{ it.next_due ? ' · 下次≈' + it.next_due : '' }}</span>
              </div>
            </div>
            <div class="rec-right">
              <div class="rec-amt">¥{{ fmt(it.monthly_cost) }}<span class="per">/月</span></div>
              <div class="rec-each">单次 ¥{{ fmt(it.amount) }}</div>
            </div>
          </div>
        </div>
        <p class="tip"><i class="fas fa-circle-info"></i> 口径:仅在真实消费里识别。固定大额(房租/税费)也算定期扣费;高频但金额乱跳的普通消费(吃饭/网购)已排除。建议逐项核对，砍掉不再用的订阅。</p>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api/client'

const loading = ref(true)
const empty = ref(false)
const data = ref({ count: 0, monthly_total: 0, annual_total: 0, items: [], by_type: [] })

const COLORS = { '订阅会员': '#5856D6', '公共事业': '#34C759', '房租物业': '#FF9500', '保险': '#FF2D55', '税费': '#8E8E93', '其他定期': '#007AFF' }
function typeColor(t) { return COLORS[t] || '#007AFF' }
function fmt(v) { return (v || 0).toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 2 }) }

onMounted(async () => {
  try {
    const r = await api.getRecurring()
    if (r.empty) { empty.value = true }
    else data.value = r
  } catch (e) { empty.value = true }
  finally { loading.value = false }
})
</script>

<style scoped>
.recurring-view { max-width: 1100px; }
.state-box { text-align: center; color: #86868b; padding: 60px 20px; line-height: 1.8; }
.muted { color: #a0a0a8; font-size: 13px; }
.sum-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 16px; }
.sum-card { background: #fff; border: 1px solid #ecedf1; border-radius: 14px; padding: 16px 18px; }
.sum-label { font-size: 13px; color: #86868b; margin-bottom: 6px; }
.sum-num { font-size: 26px; font-weight: 700; color: #1d1d1f; }
.sum-num.orange { color: #FF9500; }
.sum-foot { font-size: 12px; color: #a0a0a8; margin-top: 4px; }
.type-card { grid-column: span 1; }
.type-chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 4px; }
.type-chip { display: inline-flex; align-items: center; gap: 5px; font-size: 12px; color: #444; border: 1px solid; border-radius: 999px; padding: 3px 10px; }
.type-chip .dot { width: 7px; height: 7px; border-radius: 50%; }
.type-chip b { color: #1d1d1f; }
.card { background: #fff; border: 1px solid #ecedf1; border-radius: 16px; padding: 18px 20px; }
.card-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.card-head h3 { font-size: 16px; margin: 0; display: flex; align-items: center; gap: 8px; }
.rec-list { display: flex; flex-direction: column; }
.rec-row { display: flex; align-items: center; justify-content: space-between; padding: 12px 4px; border-bottom: 1px solid #f4f4f7; }
.rec-row:last-child { border-bottom: none; }
.rec-left { display: flex; align-items: center; gap: 12px; min-width: 0; }
.rec-badge { color: #fff; font-size: 11px; padding: 3px 9px; border-radius: 7px; white-space: nowrap; }
.rec-name { display: flex; flex-direction: column; min-width: 0; }
.rec-merchant { font-size: 15px; color: #1d1d1f; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rec-sub { font-size: 12px; color: #a0a0a8; margin-top: 2px; }
.rec-right { text-align: right; white-space: nowrap; padding-left: 12px; }
.rec-amt { font-size: 17px; font-weight: 600; color: #1d1d1f; }
.rec-amt .per { font-size: 12px; color: #a0a0a8; font-weight: 400; }
.rec-each { font-size: 12px; color: #a0a0a8; }
.tip { margin: 14px 0 0; font-size: 12.5px; color: #86868b; line-height: 1.6; }
@media (max-width: 768px) { .sum-row { grid-template-columns: 1fr; } }
</style>
