<template>
  <!-- 银行卡维度：按出资银行卡 / 钱包统计支出 -->
  <div class="analysis-card bankcard-card">
    <div class="card-header">
      <h2 class="card-title">银行卡维度</h2>
      <span class="card-subtitle">按出资银行卡 / 钱包统计支出</span>
    </div>
    <div class="card-content">
      <div v-if="bankCards.length" class="bankcard-list">
        <div v-for="(b, i) in bankCards" :key="i" class="bankcard-row">
          <span class="bank-icon" :style="{ background: b.color }">{{ b.bank.slice(0, 2) }}</span>
          <div class="bank-meta">
            <div class="bank-name">{{ b.label }}</div>
            <div class="bank-bar-wrap">
              <div class="bank-bar" :style="{ width: bankPct(b) + '%', background: b.color }"></div>
            </div>
          </div>
          <div class="bank-amt">
            <div class="bank-money">¥{{ formatMoney(b.amount) }}</div>
            <div class="bank-count">{{ b.count }}笔</div>
          </div>
        </div>
      </div>
      <div v-else class="empty-hint">暂无银行卡数据</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { formatMoney } from '@/utils/format'

const props = defineProps({
  // 银行卡分析数据数组
  bankCardAnalysis: {
    type: Array,
    default: () => [],
  },
})

// 银行卡列表
const bankCards = computed(() => props.bankCardAnalysis || [])

// 计算单条银行卡占比（相对于最大值），最小 3% 保证可见
const bankPct = (b) => {
  const max = bankCards.value.length ? bankCards.value[0].amount : 0
  return max > 0 ? Math.max(3, (b.amount / max) * 100) : 0
}
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

/* 银行卡维度 */
.card-subtitle {
  font-size: 12px;
  color: #8e8e93;
  margin-left: 8px;
}
.bankcard-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 4px 2px;
}
.bankcard-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.bank-icon {
  flex: 0 0 auto;
  width: 40px;
  height: 40px;
  border-radius: 10px;
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
}
.bank-meta {
  flex: 1 1 auto;
  min-width: 0;
}
.bank-name {
  font-size: 14px;
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.bank-bar-wrap {
  height: 8px;
  background: #f0f0f2;
  border-radius: 4px;
  overflow: hidden;
}
.bank-bar {
  height: 100%;
  border-radius: 4px;
  transition: width 0.6s ease;
}
.bank-amt {
  flex: 0 0 auto;
  text-align: right;
}
.bank-money {
  font-size: 14px;
  font-weight: 700;
  color: #1d1d1f;
}
.bank-count {
  font-size: 12px;
  color: #8e8e93;
}
.empty-hint {
  color: #8e8e93;
  text-align: center;
  padding: 24px 0;
}
</style>
