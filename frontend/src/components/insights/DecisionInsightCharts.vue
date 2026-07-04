<template>
  <!-- 决策心理：象限图 + 和弦图 + 漏斗图 -->
  <div>
    <div class="viz-section-header">
      <div class="section-subtitle"><i class="fas fa-brain"></i> 决策心理</div>
    </div>

    <!-- 象限图 -->
    <div class="analysis-card full-width-viz-card" style="height: 600px;">
      <div class="card-header">
        <h2 class="card-title">消费象限 (频次 vs 均价)</h2>
      </div>
      <div class="card-content" ref="quadrantChartRef"></div>
    </div>

    <!-- 和弦图 + 漏斗图 -->
    <div class="viz-row">
      <div class="analysis-card">
        <div class="card-header">
          <h2 class="card-title">消费关联和弦</h2>
        </div>
        <div class="card-content" ref="chordChartRef"></div>
      </div>

      <div class="analysis-card">
        <div class="card-header">
          <h2 class="card-title">消费金额漏斗</h2>
        </div>
        <div class="card-content" ref="funnelChartRef"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { formatMoney, getCategoryColor } from '@/utils/format'
import * as echarts from 'echarts'

const props = defineProps({
  // 象限图数据：数组
  quadrantData: {
    type: Array,
    default: null,
  },
  // 和弦图数据：{ nodes, links }
  chordData: {
    type: Object,
    default: null,
  },
  // 漏斗图数据：数组
  funnelData: {
    type: Array,
    default: null,
  },
})

const quadrantChartRef = ref(null)
const chordChartRef = ref(null)
const funnelChartRef = ref(null)

let quadrantChart = null
let chordChart = null
let funnelChart = null

function renderQuadrantChart(data) {
  if (!quadrantChart || !data || data.length === 0) return

  const avgFreq = data.reduce((sum, item) => sum + (item.frequency || 0), 0) / data.length
  const avgAmount = data.reduce((sum, item) => sum + (item.avg_amount || 0), 0) / data.length

  const option = {
    tooltip: {
      formatter: (params) => {
        const item = params.data
        return `
          <div style="font-weight:bold;margin-bottom:5px;">${item.name}</div>
          分类：${item.category}<br/>
          频次：${item.frequency} 次<br/>
          均价：¥${formatMoney(item.avg_amount)}<br/>
          总额：¥${formatMoney(item.total_amount)}
        `
      }
    },
    grid: {
      left: '5%',
      right: '10%',
      bottom: '10%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      name: '消费频次 (次)',
      type: 'log',
      logBase: 2,
      splitLine: {
        lineStyle: {
          type: 'dashed'
        }
      }
    },
    yAxis: {
      name: '单笔均价 (元)',
      type: 'log',
      logBase: 2,
      splitLine: {
        lineStyle: {
          type: 'dashed'
        }
      }
    },
    series: [{
      type: 'scatter',
      data: data.map(item => ({
        ...item,
        value: [item.frequency, item.avg_amount],
        symbolSize: Math.max(10, Math.min(Math.log(item.total_amount || 1) * 5, 60)),
        itemStyle: {
          color: getCategoryColor(item.category),
          shadowBlur: 10,
          shadowColor: 'rgba(0, 0, 0, 0.2)'
        }
      })),
      markLine: {
        silent: true,
        lineStyle: {
          color: '#999',
          type: 'solid',
          width: 1
        },
        data: [
          { xAxis: avgFreq, name: '平均频次' },
          { yAxis: avgAmount, name: '平均均价' }
        ]
      }
    }]
  }

  quadrantChart.setOption(option, true)
}

function renderChordChart(data) {
  if (!chordChart || !data || !data.nodes || data.nodes.length === 0) return

  let maxValue = 0
  let minValue = Infinity
  data.links.forEach(link => {
    maxValue = Math.max(maxValue, link.value || 0)
    minValue = Math.min(minValue, link.value || 0)
  })

  const coloredNodes = data.nodes.map(node => ({
    ...node,
    itemStyle: {
      color: getCategoryColor(node.name)
    }
  }))

  const processedLinks = (data.links || []).map(link => {
    let width = 1
    if (maxValue > minValue) {
      width = 1 + ((link.value || 0) - minValue) / (maxValue - minValue) * 7
    }
    return {
      ...link,
      lineStyle: {
        width: width,
        color: getCategoryColor(link.target),
        curveness: 0.3,
        opacity: 0.7
      },
      emphasis: {
        lineStyle: {
          width: width + 3,
          opacity: 1
        }
      }
    }
  })

  const option = {
    tooltip: {
      formatter: (params) => {
        if (params.dataType === 'edge') {
          return params.data.source + ' -> ' + params.data.target + '<br/>消费金额: ¥' + formatMoney(params.data.value)
        } else {
          return params.name
        }
      }
    },
    series: [{
      type: 'graph',
      layout: 'circular',
      circular: {
        rotateLabel: true
      },
      data: coloredNodes,
      links: processedLinks,
      roam: false,
      zoom: 0.75,
      label: {
        show: true,
        position: 'right',
        formatter: '{b}'
      },
      emphasis: {
        focus: 'adjacency',
        lineStyle: {
          opacity: 1
        }
      },
      blur: {
        itemStyle: {
          opacity: 0.1
        },
        lineStyle: {
          opacity: 0.1
        }
      }
    }]
  }

  chordChart.setOption(option, true)
}

function renderFunnelChart(data) {
  if (!funnelChart || !data || data.length === 0) return

  const option = {
    tooltip: {
      trigger: 'item',
      formatter: (params) => {
        return params.name + ': ¥' + formatMoney(params.value) + ' (' + params.percent + '%)'
      }
    },
    series: [{
      name: '消费漏斗',
      type: 'funnel',
      left: '10%',
      top: 60,
      bottom: 60,
      width: '80%',
      min: 0,
      max: data[0].value,
      minSize: '0%',
      maxSize: '100%',
      sort: 'descending',
      gap: 2,
      label: {
        show: true,
        position: 'inside',
        formatter: '{b}'
      },
      itemStyle: {
        borderColor: '#fff',
        borderWidth: 1
      },
      data: data
    }]
  }

  funnelChart.setOption(option, true)
}

function renderAll() {
  renderQuadrantChart(props.quadrantData)
  renderChordChart(props.chordData)
  renderFunnelChart(props.funnelData)
}

function handleResize() {
  quadrantChart?.resize()
  chordChart?.resize()
  funnelChart?.resize()
}

onMounted(() => {
  if (quadrantChartRef.value) quadrantChart = echarts.init(quadrantChartRef.value)
  if (chordChartRef.value) chordChart = echarts.init(chordChartRef.value)
  if (funnelChartRef.value) funnelChart = echarts.init(funnelChartRef.value)
  renderAll()
  window.addEventListener('resize', handleResize)
})

watch(() => [props.quadrantData, props.chordData, props.funnelData], () => {
  renderAll()
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  quadrantChart?.dispose()
  chordChart?.dispose()
  funnelChart?.dispose()
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
