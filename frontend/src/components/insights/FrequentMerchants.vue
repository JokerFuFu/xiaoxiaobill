<template>
  <!-- 最常光顾 -->
  <div class="analysis-card merchant-list-card">
    <div class="card-header">
      <h2 class="card-title">最常光顾</h2>
    </div>
    <div class="card-content">
      <div class="merchant-list" ref="merchantList">
        <!-- 动态内容 -->
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { formatMoney } from '@/utils/format'

const props = defineProps({
  // 常去商家列表（merchant_analysis.frequent_merchants）
  merchants: {
    type: Array,
    default: () => [],
  },
})

const merchantList = ref(null)

function updateMerchants() {
  if (!merchantList.value) return

  const merchants = props.merchants || []

  merchantList.value.innerHTML = merchants.map((merchant, index) => `
    <div class="merchant-item ${index < 3 ? 'top-' + (index + 1) : ''}">
      <div class="merchant-info">
        <div class="merchant-rank">${index + 1}</div>
        <div class="merchant-details">
          <div class="merchant-name">${merchant.name}</div>
          <div class="merchant-meta">上次消费: ${merchant.last_visit || '-'}</div>
        </div>
      </div>
      <div class="merchant-stats">
        <div class="stat-group">
          <div class="label">消费金额</div>
          <div class="value">${formatMoney(merchant.amount)}</div>
        </div>
        <div class="stat-group">
          <div class="label">消费次数</div>
          <div class="value">${merchant.count}次</div>
        </div>
      </div>
    </div>
  `).join('')
}

onMounted(() => {
  updateMerchants()
})

watch(() => props.merchants, () => {
  updateMerchants()
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

/* 商家列表 */
.merchant-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.merchant-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: var(--bg-color);
  border-radius: var(--radius-sm);
}

.merchant-item.top-1 .merchant-rank {
  background: linear-gradient(135deg, #FFD700, #FFA500);
}

.merchant-item.top-2 .merchant-rank {
  background: linear-gradient(135deg, #C0C0C0, #A0A0A0);
}

.merchant-item.top-3 .merchant-rank {
  background: linear-gradient(135deg, #CD7F32, #B87333);
}

.merchant-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.merchant-rank {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  color: white;
  font-weight: 600;
  font-size: 13px;
}

.merchant-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-color);
}

.merchant-meta {
  font-size: 12px;
  color: var(--secondary-text);
}

.merchant-stats {
  display: flex;
  gap: 16px;
}

.stat-group {
  text-align: right;
}

.stat-group .label {
  font-size: 11px;
  color: var(--secondary-text);
}

.stat-group .value {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-color);
}
</style>
