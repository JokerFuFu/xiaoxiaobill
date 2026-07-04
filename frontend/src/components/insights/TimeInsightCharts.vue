<template>
  <!-- 时间密码：河流图 + 热力图 + 雷达图 -->
  <div>
    <div class="viz-section-header">
      <div class="section-subtitle"><i class="fas fa-clock"></i> 时间密码</div>
    </div>

    <!-- 河流图 -->
    <div class="analysis-card full-width-viz-card">
      <div class="card-header">
        <h2 class="card-title">消费趋势河流</h2>
      </div>
      <div class="card-content" ref="themeRiverChartRef"></div>
    </div>

    <!-- 热力图 + 雷达图 -->
    <div class="viz-row">
      <div class="analysis-card">
        <div class="card-header">
          <h2 class="card-title">消费生物钟 (热力图)</h2>
        </div>
        <div class="card-content" ref="heatmapChartRef"></div>
      </div>

      <div class="analysis-card">
        <div class="card-header">
          <h2 class="card-title">季度消费结构</h2>
        </div>
        <div class="card-content" ref="radarChartRef"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { formatMoney, getCategoryColor } from '@/utils/format'
import * as echarts from 'echarts'

const props = defineProps({
  // 河流图数据：{ data, categories }
  themeriverData: {
    type: Object,
    default: null,
  },
  // 热力图数据：二维数组
  heatmapData: {
    type: Array,
    default: null,
  },
  // 雷达图数据：{ indicator, series }
  radarData: {
    type: Object,
    default: null,
  },
})

const themeRiverChartRef = ref(null)
const heatmapChartRef = ref(null)
const radarChartRef = ref(null)

let themeRiverChart = null
let heatmapChart = null
let radarChart = null

function renderThemeRiver(data) {
  if (!themeRiverChart || !data || !data.data || data.data.length === 0) return

  const themeRiverData = data.data.map(item => [item[0], item[2], item[1]])
  const colors = data.categories.map(cat => getCategoryColor(cat))

  const option = {
    color: colors,
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'line',
        lineStyle: {
          color: 'rgba(0,0,0,0.2)',
          width: 1,
          type: 'solid'
        }
      },
      formatter: (params) => {
        if (!params || params.length === 0) return ''
        const date = new Date(params[0].axisValue)
        const dateStr = date.getFullYear() + '-' + (date.getMonth() + 1).toString().padStart(2, '0')

        let result = '<div style="font-weight:bold;margin-bottom:5px;">' + dateStr + '</div>'
        const sortedParams = [...params].sort((a, b) => b.value[1] - a.value[1])

        sortedParams.forEach(item => {
          const name = item.value[2]
          const value = item.value[1]
          result += '<div style="display:flex;justify-content:space-between;align-items:center;min-width:150px;">' +
            '<span>' + item.marker + ' ' + name + '</span>' +
            '<span style="font-weight:bold;margin-left:15px;">¥' + formatMoney(value) + '</span>' +
            '</div>'
        })
        return result
      }
    },
    legend: {
      data: data.categories,
      top: 10,
      textStyle: {
        fontSize: 12
      }
    },
    singleAxis: {
      top: 50,
      bottom: 50,
      axisTick: {},
      axisLabel: {},
      type: 'time',
      axisPointer: {
        animation: true,
        label: {
          show: true
        }
      },
      splitLine: {
        show: true,
        lineStyle: {
          type: 'dashed',
          opacity: 0.2
        }
      }
    },
    series: [{
      type: 'themeRiver',
      emphasis: {
        itemStyle: {
          shadowBlur: 20,
          shadowColor: 'rgba(0, 0, 0, 0.8)'
        }
      },
      data: themeRiverData
    }]
  }

  themeRiverChart.setOption(option, true)
}

function renderHeatmap(data) {
  if (!heatmapChart || !data || data.length === 0) return

  const hours = Array.from({ length: 24 }, (_, i) => i + '点')
  const days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
  const maxValue = Math.max(...data.map(item => item[2]))

  const option = {
    tooltip: {
      position: 'top',
      formatter: (params) => {
        return `${days[params.value[1]]} ${hours[params.value[0]]}<br />消费频次: ${params.value[2]}`
      }
    },
    grid: {
      height: '50%',
      top: '10%',
      left: '15%'
    },
    xAxis: {
      type: 'category',
      data: hours,
      splitArea: {
        show: true
      },
      axisLabel: {
        interval: 2
      }
    },
    yAxis: {
      type: 'category',
      data: days,
      splitArea: {
        show: true
      }
    },
    visualMap: {
      min: 0,
      max: maxValue,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: '0%',
      inRange: {
        color: ['#f0f9ff', '#bae6fd', '#0ea5e9', '#0284c7']
      }
    },
    series: [{
      name: 'Punch Card',
      type: 'heatmap',
      data: data,
      label: {
        show: false
      },
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowColor: 'rgba(0, 0, 0, 0.5)'
        }
      }
    }]
  }

  heatmapChart.setOption(option, true)
}

function renderRadarChart(data) {
  if (!radarChart || !data || !data.indicator || data.indicator.length === 0) return

  const option = {
    tooltip: {
      trigger: 'item',
      formatter: (params) => {
        let res = params.name + '<br/>'
        data.indicator.forEach((item, index) => {
          res += item.name + ': ¥' + formatMoney(params.value[index]) + '<br/>'
        })
        return res
      }
    },
    legend: {
      data: data.series.map(item => item.name),
      top: 10
    },
    radar: {
      indicator: data.indicator,
      radius: '65%'
    },
    series: [{
      name: '季度消费结构',
      type: 'radar',
      data: data.series
    }]
  }

  radarChart.setOption(option, true)
}

function renderAll() {
  renderThemeRiver(props.themeriverData)
  renderHeatmap(props.heatmapData)
  renderRadarChart(props.radarData)
}

function handleResize() {
  themeRiverChart?.resize()
  heatmapChart?.resize()
  radarChart?.resize()
}

onMounted(() => {
  if (themeRiverChartRef.value) themeRiverChart = echarts.init(themeRiverChartRef.value)
  if (heatmapChartRef.value) heatmapChart = echarts.init(heatmapChartRef.value)
  if (radarChartRef.value) radarChart = echarts.init(radarChartRef.value)
  renderAll()
  window.addEventListener('resize', handleResize)
})

watch(() => [props.themeriverData, props.heatmapData, props.radarData], () => {
  renderAll()
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  themeRiverChart?.dispose()
  heatmapChart?.dispose()
  radarChart?.dispose()
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

.viz-section-header {
  margin: 30px 0 16px 0;
}

.section-subtitle {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: var(--secondary-text);
}

.full-width-viz-card {
  grid-column: 1 / -1;
}

.viz-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

@media (max-width: 1200px) {
  .viz-row {
    grid-template-columns: 1fr;
  }
}
</style>
