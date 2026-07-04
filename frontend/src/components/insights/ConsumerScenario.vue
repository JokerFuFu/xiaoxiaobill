<template>
  <!-- 消费场景 -->
  <div class="analysis-card scenario-card">
    <div class="card-header">
      <h2 class="card-title">消费场景</h2>
    </div>
    <div class="card-content">
      <div class="scenario-tabs">
        <button class="tab-btn" :class="{ active: currentScenario === 'channel' }" @click="setScenario('channel')">消费渠道</button>
        <button class="tab-btn" :class="{ active: currentScenario === 'time' }" @click="setScenario('time')">时段分布</button>
        <button class="tab-btn" :class="{ active: currentScenario === 'amount' }" @click="setScenario('amount')">金额层级</button>
        <button class="tab-btn" :class="{ active: currentScenario === 'payment' }" @click="setScenario('payment')">支付方式</button>
      </div>
      <div ref="chartRef" class="chart-container"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { formatMoney } from '@/utils/format'
import * as echarts from 'echarts'

const props = defineProps({
  // 场景分析数据（渠道/时段/层级）
  scenarioAnalysis: {
    type: Array,
    default: () => [],
  },
  // 支付方式分析数据
  paymentAnalysis: {
    type: Array,
    default: () => [],
  },
})

const currentScenario = ref('channel')
const chartRef = ref(null)
let chart = null

function setScenario(type) {
  currentScenario.value = type
  updateScenarioChart()
}

function updateScenarioChart() {
  if (!chart) return

  const scenarioData = props.scenarioAnalysis || []
  const paymentData = props.paymentAnalysis || []

  const groupedData = {
    'channel': scenarioData.filter(item => item.category === '渠道'),
    'time': scenarioData.filter(item => item.category === '时段'),
    'amount': scenarioData.filter(item => item.category === '层级'),
    'payment': paymentData.map(item => ({
      name: item.name,
      value: item.total_amount
    }))
  }

  const chartData = groupedData[currentScenario.value] || []
  const total = chartData.reduce((sum, item) => sum + (item.value || 0), 0)

  const colorSchemes = {
    channel: ['#007AFF', '#5856D6'],
    time: ['#FF9500', '#FF3B30', '#34C759', '#5856D6', '#007AFF', '#FF2D55'],
    amount: ['#FF3B30', '#FF9500', '#34C759', '#007AFF'],
    payment: ['#007AFF', '#FF9500', '#34C759', '#5856D6', '#FF3B30', '#FF2D55', '#64D2FF']
  }

  const option = {
    tooltip: {
      trigger: 'item',
      formatter: (params) => {
        const percentage = ((params.value / total) * 100).toFixed(2)
        return `${params.name}<br/>金额：${formatMoney(params.value)}元<br/>占比：${percentage}%`
      }
    },
    series: [{
      name: '金额分布',
      type: 'pie',
      radius: ['25%', '60%'],
      center: ['50%', '50%'],
      avoidLabelOverlap: true,
      itemStyle: {
        borderRadius: 5,
        borderColor: '#fff',
        borderWidth: 2
      },
      label: {
        show: true,
        position: 'outside',
        formatter: (params) => {
          const percentage = ((params.value / total) * 100).toFixed(2)
          return percentage > 1 ? `${params.name}\n${percentage}%` : ''
        },
        fontSize: 12,
        color: '#666',
        lineHeight: 16
      },
      labelLine: {
        show: (params) => ((params.value / total) * 100) > 1,
        length: 8,
        length2: 8,
        smooth: true,
        maxSurfaceAngle: 80
      },
      data: chartData.map((item, index) => ({
        name: item.name,
        value: item.value,
        itemStyle: {
          color: colorSchemes[currentScenario.value][index % colorSchemes[currentScenario.value].length]
        }
      }))
    }]
  }

  chart.setOption(option, true)
}

function handleResize() {
  chart?.resize()
}

onMounted(() => {
  if (chartRef.value) {
    chart = echarts.init(chartRef.value)
  }
  updateScenarioChart()
  window.addEventListener('resize', handleResize)
})

// 数据变化时重新渲染当前选中的场景
watch(() => [props.scenarioAnalysis, props.paymentAnalysis], () => {
  updateScenarioChart()
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
})
</script>

<style scoped>
.analysis-card {
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-card);
}

.card-header {
  margin-bottom: 16px;
}

.card-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-color);
  margin: 0;
}

.card-content {
  min-height: 200px;
}

/* 消费场景 */
.scenario-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.tab-btn {
  padding: 6px 12px;
  border: 1px solid var(--border-color);
  border-radius: 16px;
  background: var(--bg-color);
  color: var(--secondary-text);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.tab-btn:hover {
  background: var(--hover-bg);
}

.tab-btn.active {
  background: var(--primary-color);
  color: white;
  border-color: var(--primary-color);
}

.chart-container {
  height: 300px;
}
</style>
