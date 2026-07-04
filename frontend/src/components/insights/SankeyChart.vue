<template>
  <!-- 资金流向全景（桑基图） -->
  <div class="analysis-card sankey-card">
    <div class="card-header">
      <h2 class="card-title">资金流向全景</h2>
    </div>
    <div class="card-content" ref="chartRef"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { formatMoney } from '@/utils/format'
import * as echarts from 'echarts'

const props = defineProps({
  // 桑基图数据：{ nodes, links }
  sankeyData: {
    type: Object,
    default: null,
  },
})

const chartRef = ref(null)
let chart = null

// 渲染桑基图（逻辑与拆分前完全一致）
function renderSankeyChart(data) {
  if (!chart || !data || !data.nodes || data.nodes.length === 0) return

  const option = {
    tooltip: {
      trigger: 'item',
      triggerOn: 'mousemove',
      formatter: function (params) {
        if (params.dataType === 'edge') {
          return `${params.data.source} > ${params.data.target}<br/>金额: ${formatMoney(params.data.value)} 元`
        } else {
          return `${params.name}<br/>金额: ${formatMoney(params.data.value || params.value)} 元`
        }
      }
    },
    series: [{
      type: 'sankey',
      layoutIterations: 0,  // 禁止自动优化布局，严格按照数据顺序排列，避免连线交叉
      nodeGap: 12,          // 增加节点间距
      data: data.nodes,
      links: data.links,
      emphasis: {
        focus: 'adjacency'
      },
      lineStyle: {
        color: 'gradient',
        curveness: 0.5
      },
      label: {
        color: 'rgba(0,0,0,0.7)',
        fontFamily: 'Arial'
      }
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
  renderSankeyChart(props.sankeyData)
  window.addEventListener('resize', handleResize)
})

// 数据变化时重新渲染
watch(() => props.sankeyData, (val) => {
  renderSankeyChart(val)
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

/* 桑基图卡片 */
.sankey-card {
  flex: 1;
  height: 100%;
  margin-bottom: 0 !important;
}

@media (max-width: 1200px) {
  .sankey-card {
    height: 400px;
  }
}
</style>
