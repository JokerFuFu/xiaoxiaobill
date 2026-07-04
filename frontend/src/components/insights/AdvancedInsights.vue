<template>
  <!-- 高级洞察网格：拿铁因子 / 隐形订阅 / 消费通胀 / 品牌忠诚 / 周末效应 -->
  <div class="advanced-insights-grid">
    <!-- 拿铁因子 -->
    <div class="analysis-card insight-card latte-card">
      <div class="card-header">
        <h2 class="card-title">拿铁因子</h2>
      </div>
      <div class="card-content" ref="latteContent"></div>
    </div>

    <!-- 隐形订阅 -->
    <div class="analysis-card insight-card sub-card">
      <div class="card-header">
        <h2 class="card-title">隐形订阅</h2>
      </div>
      <div class="card-content" ref="subContent"></div>
    </div>

    <!-- 个人通胀 -->
    <div class="analysis-card insight-card inflation-card">
      <div class="card-header">
        <h2 class="card-title">消费通胀</h2>
      </div>
      <div class="card-content" ref="inflationContent"></div>
    </div>

    <!-- 品牌忠诚度 -->
    <div class="analysis-card insight-card loyalty-card">
      <div class="card-header">
        <h2 class="card-title">品牌忠诚</h2>
      </div>
      <div class="card-content" ref="loyaltyContent"></div>
    </div>

    <!-- 周末效应 -->
    <div class="analysis-card insight-card weekend-card">
      <div class="card-header">
        <h2 class="card-title">周末效应</h2>
      </div>
      <div class="card-content" ref="weekendContent"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { formatMoney } from '@/utils/format'

const props = defineProps({
  // 拿铁因子
  latteFactor: {
    type: Object,
    default: () => ({}),
  },
  // 隐形订阅
  subscriptionAnalysis: {
    type: Array,
    default: () => [],
  },
  // 个人通胀
  inflationAnalysis: {
    type: Object,
    default: () => ({}),
  },
  // 品牌忠诚度
  brandLoyalty: {
    type: Object,
    default: () => ({}),
  },
  // 周末效应
  weekendMonday: {
    type: Object,
    default: () => ({}),
  },
})

const latteContent = ref(null)
const subContent = ref(null)
const inflationContent = ref(null)
const loyaltyContent = ref(null)
const weekendContent = ref(null)

function updateAdvancedInsights() {
  // 拿铁因子
  const latte = props.latteFactor || {}
  if (latteContent.value) {
    latteContent.value.innerHTML = `
      <div class="insight-stat-big">${formatMoney(latte.total_amount || 0)}</div>
      <div class="insight-desc">累计在 <span class="highlight">${latte.top_merchant || '-'}</span> 等小额消费上花费</div>
      <div class="insight-meta">相当于 ${Math.floor((latte.total_amount || 0) / 30)} 杯咖啡</div>
    `
  }

  // 隐形订阅
  const subs = props.subscriptionAnalysis || []
  if (subContent.value) {
    if (subs.length > 0) {
      const totalAnnual = subs.reduce((sum, item) => sum + (item.annual_amount || 0), 0)
      subContent.value.innerHTML = `
        <div class="insight-stat-big">${formatMoney(totalAnnual)}</div>
        <div class="insight-desc">预估年化订阅总支出</div>
        <div class="insight-list">
          ${subs.slice(0, 2).map(s => `
            <div class="insight-item">
              <span>${s.name}</span>
              <span>${formatMoney(s.monthly_amount)}/月</span>
            </div>
          `).join('')}
        </div>
      `
    } else {
      subContent.value.innerHTML = `<div class="empty-state">未发现明显订阅支出</div>`
    }
  }

  // 个人通胀
  const inf = props.inflationAnalysis || {}
  if (inflationContent.value) {
    const trendIcon = inf.trend === 'up' ? 'fa-arrow-up' : (inf.trend === 'down' ? 'fa-arrow-down' : 'fa-minus')
    const trendColor = inf.trend === 'up' ? '#FF3B30' : (inf.trend === 'down' ? '#34C759' : '#8E8E93')
    inflationContent.value.innerHTML = `
      <div class="insight-stat-big" style="color: ${trendColor}">
        <i class="fas ${trendIcon}"></i> ${Math.abs(inf.rate || 0).toFixed(2)}%
      </div>
      <div class="insight-desc">季度客单价变化趋势</div>
      <div class="insight-meta">从 ${formatMoney(inf.first_avg || 0)} 变动至 ${formatMoney(inf.last_avg || 0)}</div>
    `
  }

  // 品牌忠诚度
  const loyalty = props.brandLoyalty || {}
  if (loyaltyContent.value && loyalty.top_amount) {
    loyaltyContent.value.innerHTML = `
      <div class="loyalty-row">
        <div class="loyalty-item">
          <div class="loyalty-value">${loyalty.top_amount.name || '-'}</div>
          <div class="loyalty-details">
            <span class="loyalty-amount">${formatMoney(loyalty.top_amount.value || 0)}</span>
            <span class="loyalty-tag">真金白银</span>
          </div>
        </div>
        <div class="loyalty-item">
          <div class="loyalty-value">${loyalty.top_count?.name || '-'}</div>
          <div class="loyalty-details">
            <span class="loyalty-amount">${loyalty.top_count.value || 0}次</span>
            <span class="loyalty-tag">最为长情</span>
          </div>
        </div>
      </div>
    `
  }

  // 周末效应
  const wm = props.weekendMonday || {}
  if (weekendContent.value) {
    const wmRatio = wm.ratio || 0
    let wmDesc = "平稳型"
    if (wmRatio > 1.5) wmDesc = "周末狂欢型"
    else if (wmRatio < 0.8) wmDesc = "周一补偿型"

    weekendContent.value.innerHTML = `
      <div class="insight-stat-big">${wmRatio.toFixed(2)}x</div>
      <div class="insight-desc">周末日均消费是周一的倍数</div>
      <div class="insight-meta">类型: ${wmDesc}</div>
    `
  }
}

onMounted(() => {
  updateAdvancedInsights()
})

watch(
  () => [
    props.latteFactor,
    props.subscriptionAnalysis,
    props.inflationAnalysis,
    props.brandLoyalty,
    props.weekendMonday,
  ],
  () => {
    updateAdvancedInsights()
  }
)
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

/* 高级洞察网格 */
.advanced-insights-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 20px;
  margin-bottom: 20px;
}

.insight-card {
  min-height: 180px;
}

.insight-stat-big {
  font-size: 32px;
  font-weight: 600;
  color: var(--text-color);
  text-align: center;
  margin-bottom: 8px;
}

.highlight {
  color: var(--primary-color);
  font-weight: 600;
}

.insight-desc {
  font-size: 13px;
  color: var(--secondary-text);
  text-align: center;
  margin-bottom: 4px;
}

.insight-meta {
  font-size: 12px;
  color: var(--text-color);
  text-align: center;
  opacity: 0.7;
}

.insight-list {
  margin-top: 12px;
}

.insight-item {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  font-size: 12px;
  border-bottom: 1px solid var(--border-color);
}

.empty-state {
  text-align: center;
  padding: 20px;
  color: var(--secondary-text);
  font-size: 13px;
}

/* 忠诚度 */
.loyalty-row {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.loyalty-item {
  text-align: center;
}

.loyalty-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-color);
  margin-bottom: 4px;
}

.loyalty-details {
  display: flex;
  justify-content: center;
  gap: 8px;
  font-size: 12px;
}

.loyalty-amount {
  color: var(--text-color);
}

.loyalty-tag {
  padding: 2px 8px;
  background: var(--primary-color);
  color: white;
  border-radius: 10px;
}

@media (max-width: 1200px) {
  .advanced-insights-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
