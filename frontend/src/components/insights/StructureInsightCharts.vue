<template>
  <!-- 结构解析：帕累托图 + 词云图 + 箱形图 -->
  <div>
    <div class="viz-section-header">
      <div class="section-subtitle"><i class="fas fa-chart-pie"></i> 结构解析</div>
    </div>

    <!-- 帕累托图 -->
    <div class="analysis-card full-width-viz-card">
      <div class="card-header">
        <h2 class="card-title">核心支出来源 (帕累托图)</h2>
      </div>
      <div class="card-content" ref="paretoChartRef" style="height: 400px;"></div>
    </div>

    <!-- 词云图 + 箱形图 -->
    <div class="viz-row">
      <div class="analysis-card">
        <div class="card-header">
          <h2 class="card-title">消费热词云</h2>
        </div>
        <div class="card-content" ref="wordCloudChartRef"></div>
      </div>

      <div class="analysis-card">
        <div class="card-header">
          <h2 class="card-title">消费分布云图</h2>
        </div>
        <div class="card-content" ref="boxPlotChartRef"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { formatMoney, getCategoryColor } from '@/utils/format'
import * as echarts from 'echarts'
import 'echarts-wordcloud'

const props = defineProps({
  // 帕累托图数据：{ categories, values, percentages }
  paretoData: {
    type: Object,
    default: null,
  },
  // 词云图数据：数组
  wordcloudData: {
    type: Array,
    default: null,
  },
  // 箱形图数据：{ data, categories, box_data }
  boxplotData: {
    type: Object,
    default: null,
  },
})

const paretoChartRef = ref(null)
const wordCloudChartRef = ref(null)
const boxPlotChartRef = ref(null)

let paretoChart = null
let wordCloudChart = null
let boxPlotChart = null

function renderParetoChart(data) {
  if (!paretoChart || !data || !data.categories || data.categories.length === 0) return

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        crossStyle: {
          color: '#999'
        }
      }
    },
    grid: {
      right: '10%',
      left: '5%',
      bottom: '10%'
    },
    legend: {
      data: ['消费金额', '累积占比']
    },
    xAxis: [{
      type: 'category',
      data: data.categories,
      axisPointer: {
        type: 'shadow'
      },
      axisLabel: {
        interval: 0,
        rotate: 0
      }
    }],
    yAxis: [{
      type: 'value',
      name: '金额'
    }, {
      type: 'value',
      name: '累积占比',
      min: 0,
      max: 100,
      interval: 20,
      axisLabel: {
        formatter: '{value} %'
      }
    }],
    series: [{
      name: '消费金额',
      type: 'bar',
      data: data.values,
      itemStyle: {
        color: (params) => getCategoryColor(params.name)
      }
    }, {
      name: '累积占比',
      type: 'line',
      yAxisIndex: 1,
      data: data.percentages,
      itemStyle: {
        color: '#5470c6'
      },
      markLine: {
        data: [{ yAxis: 80, name: '80%线' }],
        lineStyle: {
          color: '#ee6666',
          type: 'dashed'
        }
      }
    }]
  }

  paretoChart.setOption(option, true)
}

function renderWordCloud(data) {
  if (!wordCloudChart || !data || data.length === 0) return

  const option = {
    tooltip: {
      show: true,
      formatter: (params) => {
        return params.name + ': ¥' + formatMoney(params.value)
      }
    },
    series: [{
      type: 'wordCloud',
      shape: 'circle',
      left: 'center',
      top: 'center',
      width: '90%',
      height: '90%',
      sizeRange: [12, 60],
      rotationRange: [0, 0],
      rotationStep: 0,
      gridSize: 8,
      drawOutOfBound: false,
      textStyle: {
        fontFamily: 'sans-serif',
        fontWeight: 'bold',
        color: () => {
          return 'rgb(' + [
            Math.round(Math.random() * 160),
            Math.round(Math.random() * 160),
            Math.round(Math.random() * 160)
          ].join(',') + ')'
        }
      },
      emphasis: {
        focus: 'self',
        textStyle: {
          shadowBlur: 10,
          shadowColor: '#333'
        }
      },
      data: data
    }]
  }

  wordCloudChart.setOption(option, true)
}

function renderBoxPlot(data) {
  if (!boxPlotChart || !data || !data.data || data.data.length === 0) return

  const alignedCategories = ['', ...data.categories]
  const alignedBoxData = [[], ...data.box_data]

  const getSeriesConfig = (isDetailMode) => {
    const seriesData = data.data.map(item => {
      let offset = isDetailMode ? 0.35 : 0
      const jitterRange = isDetailMode ? 0.5 : 0.6
      const jitter = (Math.random() - 0.5) * jitterRange
      return {
        value: [item.c + 1 + offset + jitter, item.v],
        merchant: item.m,
        date: item.d,
        categoryName: data.categories[item.c]
      }
    })

    return {
      boxWidth: isDetailMode ? '20%' : '50%',
      scatterData: seriesData
    }
  }

  const initialConfig = getSeriesConfig(false)

  const option = {
    tooltip: {
      trigger: 'item',
      formatter: (params) => {
        if (params.seriesType === 'boxplot') {
          return `${params.name}<br/>
                  最大值: ${formatMoney(params.data[5])}<br/>
                  Q3: ${formatMoney(params.data[4])}<br/>
                  中位数: ${formatMoney(params.data[3])}<br/>
                  Q1: ${formatMoney(params.data[2])}<br/>
                  最小值: ${formatMoney(params.data[1])}`
        } else {
          const d = params.data
          return `<strong>${d.categoryName}</strong><br/>
                  ${d.date}<br/>
                  ${d.merchant}<br/>
                  <strong>¥${formatMoney(d.value[1])}</strong>`
        }
      }
    },
    grid: {
      left: '10%',
      right: '10%',
      bottom: '15%'
    },
    xAxis: [{
      type: 'category',
      data: alignedCategories,
      boundaryGap: true,
      axisLabel: {
        interval: 0,
        rotate: 0,
        formatter: (value) => {
          return value.length > 4 ? value.substring(0, 4) + '..' : value
        }
      }
    }, {
      type: 'value',
      min: -0.5,
      max: alignedCategories.length - 0.5,
      show: false
    }],
    yAxis: {
      type: 'log',
      logBase: 10,
      min: 1,
      name: '金额 (元)',
      splitLine: {
        show: true,
        lineStyle: {
          color: '#eee'
        }
      }
    },
    series: [{
      name: 'summary',
      type: 'boxplot',
      xAxisIndex: 0,
      data: alignedBoxData,
      boxWidth: initialConfig.boxWidth,
      itemStyle: {
        color: 'rgba(0, 0, 0, 0.02)',
        borderColor: '#666',
        borderWidth: 1.5
      },
      symbolSize: 0
    }, {
      name: 'transaction',
      type: 'scatter',
      xAxisIndex: 1,
      symbolSize: 6,
      itemStyle: {
        color: (params) => getCategoryColor(params.data.categoryName),
        opacity: 0.6
      },
      data: initialConfig.scatterData
    }]
  }

  boxPlotChart.setOption(option, true)
}

function renderAll() {
  renderParetoChart(props.paretoData)
  renderWordCloud(props.wordcloudData)
  renderBoxPlot(props.boxplotData)
}

function handleResize() {
  paretoChart?.resize()
  wordCloudChart?.resize()
  boxPlotChart?.resize()
}

onMounted(() => {
  if (paretoChartRef.value) paretoChart = echarts.init(paretoChartRef.value)
  if (wordCloudChartRef.value) wordCloudChart = echarts.init(wordCloudChartRef.value)
  if (boxPlotChartRef.value) boxPlotChart = echarts.init(boxPlotChartRef.value)
  renderAll()
  window.addEventListener('resize', handleResize)
})

watch(() => [props.paretoData, props.wordcloudData, props.boxplotData], () => {
  renderAll()
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  paretoChart?.dispose()
  wordCloudChart?.dispose()
  boxPlotChart?.dispose()
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
