<template>
  <div class="recurring-view">
    <div v-if="loading" class="state-box">识别中…</div>
    <div v-else-if="empty" class="state-box">还没有账单数据，先去上传。</div>

    <template v-else>
      <!-- 汇总 -->
      <div v-if="data.count" class="sum-row">
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
      <div v-if="data.count" class="card">
        <div class="card-head"><h3><i class="fas fa-repeat" style="color:#5856D6"></i> 识别到的订阅 / 定期扣费</h3>
          <span class="muted">按月成本排序</span></div>
        <div class="rec-list">
          <div v-for="(it, i) in data.items" :key="i" class="rec-row">
            <div class="rec-left">
              <span class="rec-badge" :style="{ background: typeColor(it.type) }">{{ it.type }}</span>
              <div class="rec-name">
                <span class="rec-merchant">{{ it.merchant }}
                  <span v-if="it.via === '转账代付'" class="via-tag"><i class="fas fa-people-arrows"></i> 转账代付</span>
                </span>
                <span class="rec-sub">
                  {{ it.cadence }} · 共 {{ it.count }} 笔 / {{ it.months }} 个月 · 累计 ¥{{ fmt(it.total_paid) }}
                  <template v-if="it.parties && it.parties.length"> · 经手 {{ it.parties.join('、') }}</template>
                  <template v-if="it.next_due"> · 下次≈{{ it.next_due }}</template>
                </span>
                <span v-if="it.sample" class="rec-eg">例：{{ it.sample }}</span>
              </div>
            </div>
            <div class="rec-right">
              <div class="rec-amt">¥{{ fmt(it.monthly_cost) }}<span class="per">/月</span></div>
              <div class="rec-each">单次 ¥{{ fmt(it.amount) }}</div>
            </div>
          </div>
        </div>
        <p class="tip"><i class="fas fa-circle-info"></i> 已能识别<strong>转账给个人代充的订阅</strong>(如 GPT/Claude/Codex/Manus，按服务名归并)与房租/税费/水电等定期账单；高频但金额乱跳的普通消费(吃饭/网购)不计入。代充订阅的实际成本可结合下方「个人往来」里对方的报销看净额。</p>
      </div>
      <div v-else class="state-box">没有识别到明显的订阅或定期扣费。</div>

      <!-- 个人往来对账 -->
      <div v-if="peers.length" class="card">
        <div class="card-head">
          <h3><i class="fas fa-people-arrows" style="color:#34C759"></i> 个人往来对账</h3>
          <div class="peer-search">
            <input v-model.trim="peerQuery" placeholder="搜索某人的名字" @keyup.enter="searchPeer" />
            <button @click="searchPeer"><i class="fas fa-search"></i></button>
            <button v-if="queried" class="clear" @click="clearPeer">清除</button>
          </div>
        </div>
        <p class="muted peer-hint">和每个人之间的钱：转入(他给你) vs 转出(你给他)，净额一眼看清谁欠谁。大额资金搬运单列，不盖过日常代付/报销。</p>
        <div class="peer-list">
          <div v-for="(p, i) in peers" :key="i" class="peer-row" :class="{ open: openPeer === i }" @click="openPeer = openPeer === i ? -1 : i">
            <div class="peer-head">
              <span class="peer-name">{{ p.name }}</span>
              <span class="peer-net" :class="p.net >= 0 ? 'pos' : 'neg'">
                净 {{ p.net >= 0 ? '+' : '-' }}¥{{ fmt(Math.abs(p.net)) }}
              </span>
            </div>
            <div class="peer-sub">
              他给你 ¥{{ fmt(p.in_total) }} · 你给他 ¥{{ fmt(p.out_total) }} · {{ p.count }} 笔
              <span v-if="p.big_in || p.big_out" class="peer-big">(含大额 进¥{{ fmt(p.big_in) }}/出¥{{ fmt(p.big_out) }}，日常净 {{ p.daily_net >= 0 ? '+' : '-' }}¥{{ fmt(Math.abs(p.daily_net)) }})</span>
            </div>
            <div v-if="openPeer === i" class="peer-detail" @click.stop>
              <div v-for="(r, j) in p.recent" :key="j" class="peer-tx">
                <span class="tx-date">{{ r.date }}</span>
                <span class="tx-dir" :class="['收入','转入'].includes(r.dir) ? 'in' : 'out'">{{ r.dir }}</span>
                <span class="tx-amt">¥{{ fmt(r.amount) }}</span>
                <span class="tx-desc">{{ r.desc || r.nature }}</span>
              </div>
            </div>
          </div>
        </div>
        <p v-if="queried && !peers.length" class="muted">没找到「{{ queried }}」的往来记录。</p>
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
const peers = ref([])
const peerQuery = ref('')
const queried = ref('')
const openPeer = ref(-1)

const COLORS = { '订阅会员': '#5856D6', '公共事业': '#34C759', '房租物业': '#FF9500', '保险': '#FF2D55', '税费': '#8E8E93', '其他定期': '#007AFF' }
function typeColor(t) { return COLORS[t] || '#007AFF' }
function fmt(v) { return (v || 0).toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 2 }) }

async function loadPeers(name) {
  try {
    const r = await api.getPeerTransfers(name ? { name } : {})
    peers.value = r.empty ? [] : (r.peers || [])
    queried.value = name || ''
    openPeer.value = -1
  } catch (e) { peers.value = [] }
}
function searchPeer() { if (peerQuery.value) loadPeers(peerQuery.value) }
function clearPeer() { peerQuery.value = ''; loadPeers() }

onMounted(async () => {
  try {
    const r = await api.getRecurring()
    if (r.empty) { empty.value = true; return }
    data.value = r
    await loadPeers()
  } catch (e) { empty.value = true }
  finally { loading.value = false }
})
</script>

<style scoped>
.recurring-view { max-width: 1100px; }
.state-box { text-align: center; color: #86868b; padding: 50px 20px; line-height: 1.8; }
.muted { color: #a0a0a8; font-size: 13px; }
.sum-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 16px; }
.sum-card { background: #fff; border: 1px solid #ecedf1; border-radius: 14px; padding: 16px 18px; }
.sum-label { font-size: 13px; color: #86868b; margin-bottom: 6px; }
.sum-num { font-size: 26px; font-weight: 700; color: #1d1d1f; }
.sum-num.orange { color: #FF9500; }
.sum-foot { font-size: 12px; color: #a0a0a8; margin-top: 4px; }
.type-chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 4px; }
.type-chip { display: inline-flex; align-items: center; gap: 5px; font-size: 12px; color: #444; border: 1px solid; border-radius: 999px; padding: 3px 10px; }
.type-chip .dot { width: 7px; height: 7px; border-radius: 50%; }
.type-chip b { color: #1d1d1f; }
.card { background: #fff; border: 1px solid #ecedf1; border-radius: 16px; padding: 18px 20px; margin-bottom: 16px; }
.card-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; gap: 10px; flex-wrap: wrap; }
.card-head h3 { font-size: 16px; margin: 0; display: flex; align-items: center; gap: 8px; }
.rec-list { display: flex; flex-direction: column; }
.rec-row { display: flex; align-items: flex-start; justify-content: space-between; padding: 12px 4px; border-bottom: 1px solid #f4f4f7; }
.rec-row:last-child { border-bottom: none; }
.rec-left { display: flex; align-items: flex-start; gap: 12px; min-width: 0; }
.rec-badge { color: #fff; font-size: 11px; padding: 3px 9px; border-radius: 7px; white-space: nowrap; margin-top: 2px; }
.rec-name { display: flex; flex-direction: column; min-width: 0; }
.rec-merchant { font-size: 15px; color: #1d1d1f; font-weight: 500; }
.via-tag { font-size: 11px; color: #34C759; background: #eafaef; border-radius: 5px; padding: 1px 6px; margin-left: 6px; font-weight: 400; }
.rec-sub { font-size: 12px; color: #a0a0a8; margin-top: 3px; line-height: 1.5; }
.rec-eg { font-size: 11.5px; color: #b8b8c0; margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 520px; }
.rec-right { text-align: right; white-space: nowrap; padding-left: 12px; }
.rec-amt { font-size: 17px; font-weight: 600; color: #1d1d1f; }
.rec-amt .per { font-size: 12px; color: #a0a0a8; font-weight: 400; }
.rec-each { font-size: 12px; color: #a0a0a8; }
.tip { margin: 14px 0 0; font-size: 12.5px; color: #86868b; line-height: 1.6; }
/* peer */
.peer-search { display: flex; gap: 6px; }
.peer-search input { height: 32px; border: 1px solid #d2d2d7; border-radius: 8px; padding: 0 10px; font-size: 13px; width: 160px; }
.peer-search button { height: 32px; border: none; background: #f0f0f3; color: #555; border-radius: 8px; padding: 0 12px; cursor: pointer; font-size: 13px; }
.peer-search button.clear { color: #007AFF; }
.peer-hint { margin: 0 0 12px; line-height: 1.6; }
.peer-list { display: flex; flex-direction: column; }
.peer-row { padding: 11px 6px; border-bottom: 1px solid #f4f4f7; cursor: pointer; border-radius: 8px; transition: background .12s; }
.peer-row:hover { background: #fafafb; }
.peer-row:last-child { border-bottom: none; }
.peer-head { display: flex; justify-content: space-between; align-items: center; }
.peer-name { font-size: 15px; font-weight: 500; color: #1d1d1f; }
.peer-net { font-size: 15px; font-weight: 600; }
.peer-net.pos { color: #34C759; }
.peer-net.neg { color: #FF3B30; }
.peer-sub { font-size: 12.5px; color: #86868b; margin-top: 3px; }
.peer-big { color: #b0b0b8; }
.peer-detail { margin-top: 8px; padding: 8px 10px; background: #f7f8fa; border-radius: 8px; }
.peer-tx { display: flex; align-items: center; gap: 10px; font-size: 12.5px; padding: 3px 0; }
.tx-date { color: #a0a0a8; width: 84px; flex-shrink: 0; }
.tx-dir { width: 32px; flex-shrink: 0; }
.tx-dir.in { color: #34C759; }
.tx-dir.out { color: #FF9500; }
.tx-amt { width: 90px; text-align: right; color: #1d1d1f; flex-shrink: 0; }
.tx-desc { color: #86868b; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
@media (max-width: 768px) { .sum-row { grid-template-columns: 1fr; } .rec-eg { max-width: 220px; } }
</style>
