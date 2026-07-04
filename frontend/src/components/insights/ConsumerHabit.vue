<template>
  <!-- 消费习惯 -->
  <div class="analysis-card habit-card">
    <div class="card-header">
      <h2 class="card-title">消费习惯</h2>
    </div>
    <div class="card-content">
      <div class="habit-stats" ref="habitStats">
        <!-- 动态内容 -->
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'

const props = defineProps({
  // 消费习惯分析
  habitAnalysis: {
    type: Object,
    default: () => ({}),
  },
  // 深夜消费分析
  nighttimeAnalysis: {
    type: Object,
    default: () => ({}),
  },
  // 恩格尔系数
  engelCoefficient: {
    type: Object,
    default: () => ({}),
  },
})

const habitStats = ref(null)

function updateHabitStats() {
  if (!habitStats.value) return

  const habit = props.habitAnalysis || {}
  const night = props.nighttimeAnalysis || {}
  const engel = props.engelCoefficient || {}

  habitStats.value.innerHTML = `
    <div class="stat-item">
      <div class="stat-value">${habit.daily_avg?.toFixed(2) || 0}</div>
      <div class="stat-label">日均消费(元)</div>
    </div>
    <div class="stat-item">
      <div class="stat-value">${habit.weekend_ratio || 0}%</div>
      <div class="stat-label">周末消费占比</div>
    </div>
    <div class="stat-item">
      <div class="stat-value">${habit.fixed_expenses || 0}%</div>
      <div class="stat-label">固定支出占比</div>
    </div>
    <div class="stat-item">
      <div class="stat-value">${habit.month_start_ratio || 0}%</div>
      <div class="stat-label">月初消费占比</div>
    </div>
    <div class="stat-item">
      <div class="stat-value">${night.ratio?.toFixed(2) || 0}%</div>
      <div class="stat-label">深夜剁手</div>
    </div>
    <div class="stat-item">
      <div class="stat-value">${engel.ratio?.toFixed(2) || 0}%</div>
      <div class="stat-label">恩格尔系数</div>
    </div>
  `
}

onMounted(() => {
  updateHabitStats()
})

watch(() => [props.habitAnalysis, props.nighttimeAnalysis, props.engelCoefficient], () => {
  updateHabitStats()
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

/* 消费习惯 */
.habit-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.stat-item {
  text-align: center;
  padding: 12px;
  background: var(--bg-color);
  border-radius: var(--radius-sm);
}

.stat-value {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-color);
  margin-bottom: 4px;
}

.stat-label {
  font-size: 12px;
  color: var(--secondary-text);
}

@media (max-width: 768px) {
  .habit-stats {
    grid-template-columns: 1fr;
  }
}
</style>
