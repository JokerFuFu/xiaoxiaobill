<template>
  <div ref="chartRef" class="echart-container" :style="{ height, width }"></div>
</template>

<script setup>
/**
 * 通用 ECharts 封装:收敛各处重复的 init / setOption / resize 监听 / dispose 生命周期。
 *
 * 用法:父组件把「完整 option」通过 :option 传入(无数据时传 null,组件不渲染);
 * option 变化即以 notMerge 方式重绘(与既有 setOption(opt, true) 行为一致)。
 * 需要拿实例做额外操作时用 ref 调用 exposed 的 getInstance()。
 */
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  // 完整的 ECharts option;为 null/空时不渲染(保持"无数据不画"的既有行为)
  option: { type: Object, default: null },
  height: { type: String, default: '100%' },
  width: { type: String, default: '100%' },
  // 初始化主题(如需)
  theme: { type: [String, Object], default: undefined },
  // 是否随窗口自动 resize
  autoresize: { type: Boolean, default: true },
})

const chartRef = ref(null)
let chart = null

function render(option) {
  if (!chart || !option) return
  chart.setOption(option, true) // notMerge:整体替换,与既有各图表逐字一致
}

function handleResize() {
  chart?.resize()
}

onMounted(() => {
  if (chartRef.value) {
    chart = echarts.init(chartRef.value, props.theme)
    render(props.option)
    if (props.autoresize) window.addEventListener('resize', handleResize)
  }
})

watch(() => props.option, (val) => render(val))

onUnmounted(() => {
  if (props.autoresize) window.removeEventListener('resize', handleResize)
  chart?.dispose()
  chart = null
})

defineExpose({
  getInstance: () => chart,
  resize: handleResize,
})
</script>

<style scoped>
.echart-container {
  min-height: 200px;
}
</style>
