<template>
  <div class="overseas-view">
    <div class="head-row">
      <h3 class="ov-title"><i class="fas fa-earth-asia" style="color:#007AFF"></i> 境外 / 外币消费</h3>
      <select v-if="data.years && data.years.length" v-model="year" class="year-sel" @change="reload">
        <option :value="0">全部年份</option>
        <option v-for="y in data.years" :key="y" :value="y">{{ y }} 年</option>
      </select>
    </div>

    <div v-if="loading" class="state-box">识别中…</div>
    <div v-else-if="empty" class="state-box">还没有账单数据，先去上传。</div>
    <div v-else-if="!data.count" class="state-box">没有识别到境外 / 外币消费。<br />
      <span class="muted">识别依据:外币金额(如 39.00 美元)、币种代码(USD/JPY…)、信用卡境外消费的国家代码。</span></div>

    <template v-else>
      <div class="sum-row">
        <div class="sum-card">
          <div class="sum-label">境外消费合计(折人民币)</div>
          <div class="sum-num">¥{{ fmt(data.total_cny) }}</div>
          <div class="sum-foot">{{ data.count }} 笔</div>
        </div>
        <div class="sum-card" v-for="c in data.by_currency.slice(0,2)" :key="c.currency">
          <div class="sum-label">{{ c.currency }} 外币消费</div>
          <div class="sum-num blue">{{ c.foreign_total != null ? curSym(c.currency) + fmt(c.foreign_total) : '—' }}</div>
          <div class="sum-foot">{{ c.count }} 笔 · 折 ¥{{ fmt(c.cny) }}</div>
        </div>
      </div>

      <div class="grid2">
        <div class="card">
          <div class="card-head"><h4><i class="fas fa-chart-column" style="color:#5856D6"></i> 月度境外消费</h4></div>
          <div ref="chartRef" class="ov-chart"></div>
        </div>
        <div class="card">
          <div class="card-head"><h4><i class="fas fa-store" style="color:#FF9500"></i> 境外商户 Top</h4></div>
          <div class="rank-list">
            <div v-for="(m, i) in data.by_merchant.slice(0,10)" :key="i" class="rank-row">
              <span class="rank-name">{{ m.merchant }}</span>
              <span class="rank-amt">¥{{ fmt(m.cny) }} <span class="rank-cnt">×{{ m.count }}</span></span>
            </div>
          </div>
          <div v-if="data.by_region && data.by_region.length" class="region-row">
            <span v-for="r in data.by_region" :key="r.region" class="region-chip">{{ r.region }} ¥{{ fmt(r.cny) }}</span>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-head"><h4><i class="fas fa-list" style="color:#34C759"></i> 境外消费明细</h4>
          <span class="muted">最近 {{ data.list.length }} 笔</span></div>
        <div class="tbl-wrap">
          <table class="ov-tbl">
            <thead><tr><th>日期</th><th>商户</th><th>来源</th><th class="num">外币</th><th class="num">人民币</th></tr></thead>
            <tbody>
              <tr v-for="(r, i) in data.list" :key="i">
                <td class="nowrap">{{ r.date }}</td>
                <td class="mer">{{ r.merchant }}<span v-if="r.region" class="reg-tag">{{ r.region }}</span></td>
                <td class="nowrap">{{ r.source }}</td>
                <td class="num">{{ r.foreign_amount != null ? curSym(r.currency) + fmt(r.foreign_amount) : '—' }}</td>
                <td class="num">¥{{ fmt(r.cny) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, onActivated, nextTick } from 'vue'
import * as echarts from 'echarts'
import api from '@/api/client'

const loading = ref(true)
const empty = ref(false)
const year = ref(0)
const data = ref({ count: 0, total_cny: 0, years: [], by_currency: [], by_region: [], by_merchant: [], monthly: [], list: [] })
const chartRef = ref(null)
let chart = null

const SYM = { USD: '$', EUR: '€', GBP: '£', JPY: '¥', HKD: 'HK$', KRW: '₩', SGD: 'S$', AUD: 'A$', CAD: 'C$', THB: '฿', TWD: 'NT$' }
function curSym(c) { return SYM[c] || (c ? c + ' ' : '') }
function fmt(v) { return (v || 0).toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 2 }) }

function renderChart() {
  if (!chartRef.value || !data.value.monthly || !data.value.monthly.length) return
  if (!chart) chart = echarts.init(chartRef.value)
  const m = data.value.monthly
  chart.setOption({
    grid: { left: 8, right: 12, top: 18, bottom: 24, containLabel: true },
    tooltip: { trigger: 'axis', valueFormatter: v => '¥' + fmt(v) },
    xAxis: { type: 'category', data: m.map(x => x.month), axisLabel: { fontSize: 10, color: '#999' } },
    yAxis: { type: 'value', axisLabel: { fontSize: 10, color: '#999' }, splitLine: { lineStyle: { color: '#f0f0f3' } } },
    series: [{ type: 'bar', data: m.map(x => x.cny), itemStyle: { color: '#007AFF', borderRadius: [4, 4, 0, 0] }, barMaxWidth: 28 }],
  })
}

async function reload() {
  loading.value = true
  try {
    const r = await api.getOverseas(year.value ? { year: year.value } : {})
    if (r.empty) { empty.value = true }
    else { empty.value = false; data.value = r; await nextTick(); renderChart() }
  } catch (e) { empty.value = true }
  finally { loading.value = false }
}

onMounted(reload)
onActivated(() => { if (chart) { chart.resize(); renderChart() } })
window.addEventListener('resize', () => chart && chart.resize())
</script>

<style scoped>
.overseas-view { max-width: 1200px; }
.head-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.ov-title { font-size: 17px; margin: 0; display: flex; align-items: center; gap: 8px; }
.year-sel { height: 36px; border: 1px solid #d2d2d7; border-radius: 9px; padding: 0 12px; font-size: 14px; background: #fff; }
.state-box { text-align: center; color: #86868b; padding: 60px 20px; line-height: 1.9; }
.muted { color: #a0a0a8; font-size: 13px; }
.sum-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 16px; }
.sum-card { background: #fff; border: 1px solid #ecedf1; border-radius: 14px; padding: 16px 18px; }
.sum-label { font-size: 13px; color: #86868b; margin-bottom: 6px; }
.sum-num { font-size: 24px; font-weight: 700; color: #1d1d1f; }
.sum-num.blue { color: #007AFF; }
.sum-foot { font-size: 12px; color: #a0a0a8; margin-top: 4px; }
.grid2 { display: grid; grid-template-columns: 1.2fr 1fr; gap: 14px; margin-bottom: 16px; }
.card { background: #fff; border: 1px solid #ecedf1; border-radius: 16px; padding: 16px 18px; }
.card-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.card-head h4 { font-size: 15px; margin: 0; display: flex; align-items: center; gap: 7px; }
.ov-chart { height: 240px; width: 100%; }
.rank-list { display: flex; flex-direction: column; }
.rank-row { display: flex; justify-content: space-between; padding: 7px 2px; border-bottom: 1px solid #f4f4f7; font-size: 14px; }
.rank-row:last-child { border-bottom: none; }
.rank-name { color: #333; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 65%; }
.rank-amt { color: #1d1d1f; font-weight: 500; white-space: nowrap; }
.rank-cnt { color: #a0a0a8; font-size: 12px; font-weight: 400; }
.region-row { margin-top: 10px; display: flex; flex-wrap: wrap; gap: 6px; }
.region-chip { font-size: 12px; background: #f0f7ff; color: #007AFF; border-radius: 999px; padding: 3px 10px; }
.tbl-wrap { overflow-x: auto; }
.ov-tbl { width: 100%; border-collapse: collapse; font-size: 13px; }
.ov-tbl th { text-align: left; color: #a0a0a8; font-weight: 500; padding: 8px 10px; border-bottom: 1px solid #eee; }
.ov-tbl td { padding: 8px 10px; border-bottom: 1px solid #f6f6f8; color: #333; }
.ov-tbl .num { text-align: right; white-space: nowrap; }
.ov-tbl .nowrap { white-space: nowrap; }
.ov-tbl .mer { max-width: 320px; }
.reg-tag { margin-left: 6px; font-size: 11px; background: #eef; color: #5856D6; border-radius: 5px; padding: 1px 6px; }
@media (max-width: 768px) { .sum-row, .grid2 { grid-template-columns: 1fr; } }
</style>
