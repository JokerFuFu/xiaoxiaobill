<template>
  <div class="ai-chart">
    <div ref="box" class="ai-chart-box"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({ spec: { type: Object, required: true } })
const box = ref(null)
let chart = null

const PALETTE = ['#007AFF', '#34C759', '#FF9500', '#AF52DE', '#FF3B30', '#5AC8FA', '#FFCC00', '#5856D6']

function buildOption(spec) {
  const base = {
    color: PALETTE,
    title: spec.title ? {
      text: spec.title, left: 'center',
      textStyle: { fontSize: 13, fontWeight: 600, color: '#3a3a3c' }
    } : undefined,
    tooltip: { trigger: spec.type === 'pie' ? 'item' : 'axis', confine: true },
    grid: { left: 8, right: 16, top: spec.title ? 42 : 24, bottom: 8, containLabel: true }
  }

  if (spec.type === 'pie') {
    const data = (spec.data || []).map(d => ({ name: String(d.name), value: Number(d.value) || 0 }))
    return {
      ...base,
      legend: { bottom: 0, type: 'scroll', textStyle: { fontSize: 11 } },
      series: [{
        type: 'pie', radius: ['38%', '62%'], center: ['50%', '46%'],
        data,
        label: { fontSize: 11, formatter: '{b}\n{d}%' },
        itemStyle: { borderRadius: 5, borderColor: '#fff', borderWidth: 2 }
      }]
    }
  }

  const series = (spec.series || []).map(s => ({
    name: s.name || '',
    type: spec.type === 'line' ? 'line' : 'bar',
    data: (s.data || []).map(v => Number(v) || 0),
    smooth: spec.type === 'line',
    barMaxWidth: 36,
    itemStyle: spec.type === 'bar' ? { borderRadius: [5, 5, 0, 0] } : undefined,
    areaStyle: spec.type === 'line' && (spec.series || []).length === 1
      ? { opacity: 0.08 } : undefined
  }))
  return {
    ...base,
    legend: series.length > 1 ? { bottom: 0, textStyle: { fontSize: 11 } } : undefined,
    xAxis: {
      type: 'category', data: (spec.categories || []).map(String),
      axisLabel: { fontSize: 11, color: '#86868b', interval: 0, rotate: (spec.categories || []).length > 8 ? 30 : 0 },
      axisLine: { lineStyle: { color: '#e5e5ea' } }, axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      axisLabel: { fontSize: 11, color: '#86868b' },
      splitLine: { lineStyle: { color: '#f2f2f5' } }
    },
    series
  }
}

function render() {
  if (!box.value) return
  if (!chart) chart = echarts.init(box.value)
  try {
    chart.setOption(buildOption(props.spec), true)
  } catch (e) { /* 非法 spec 静默忽略 */ }
}

function onResize() { chart && chart.resize() }

onMounted(() => { render(); window.addEventListener('resize', onResize) })
onUnmounted(() => { window.removeEventListener('resize', onResize); chart && chart.dispose(); chart = null })
watch(() => props.spec, render, { deep: true })
</script>

<style scoped>
.ai-chart {
  background: #fff; border: 1px solid #ebebf0; border-radius: 12px;
  padding: 10px 6px 6px; margin: 10px 0;
}
.ai-chart-box { width: 100%; height: 260px; }
</style>
