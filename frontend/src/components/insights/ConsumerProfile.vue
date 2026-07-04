<template>
  <!-- 消费画像 -->
  <div class="analysis-card profile-card">
    <div class="card-header">
      <h2 class="card-title">消费画像</h2>
    </div>
    <div class="card-content profile-content" ref="profileContent">
      <!-- 动态内容 -->
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'

const props = defineProps({
  // 消费画像标签数据（后端返回的 tags 对象）
  tags: {
    type: Object,
    default: null,
  },
})

const profileContent = ref(null)

function updateTags() {
  const tagsData = props.tags
  if (!tagsData || !profileContent.value) return

  // 后端返回的 tags 是一个对象，包含 tags 数组和其他特征字段
  const tags = tagsData.tags || []

  const tagsHtml = `
    <div class="tag-cloud">
      ${tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
    </div>
  `

  const detailsHtml = `
    <div class="profile-details">
      <div class="profile-feature">
        <div class="feature-icon"><i class="fas fa-clock"></i></div>
        <div class="feature-content">
          <div class="feature-title">消费时间</div>
          <div class="feature-description">${formatTimePattern(tagsData.time_pattern || '-')}</div>
        </div>
      </div>
      <div class="profile-feature">
        <div class="feature-icon"><i class="fas fa-shopping-bag"></i></div>
        <div class="feature-content">
          <div class="feature-title">消费偏好</div>
          <div class="feature-description">${formatPreference(tagsData.spending_preference || '-')}</div>
        </div>
      </div>
      <div class="profile-feature">
        <div class="feature-icon"><i class="fas fa-chart-line"></i></div>
        <div class="feature-content">
          <div class="feature-title">消费规律</div>
          <div class="feature-description">${formatPattern(tagsData.spending_pattern || '-')}</div>
        </div>
      </div>
      <div class="profile-feature">
        <div class="feature-icon"><i class="fas fa-wallet"></i></div>
        <div class="feature-content">
          <div class="feature-title">消费能力</div>
          <div class="feature-description">${formatPower(tagsData.spending_power || '-')}</div>
        </div>
      </div>
    </div>
  `

  profileContent.value.innerHTML = tagsHtml + detailsHtml
}

// 格式化函数（从老前端迁移）
function formatTimePattern(text) {
  if (text === '-') return text
  return text.replace(/(夜间|早起|日间)/g, '<span class="highlight">$1</span>')
}

function formatPreference(text) {
  if (text === '-') return text
  return text.replace(/最常消费的品类是/, '')
    .replace(/([^，。]+?)(\([0-9.]+%\))/g, '<span class="highlight">$1</span><span class="percentage">$2</span>')
}

function formatPattern(text) {
  if (text === '-') return text
  return text.replace(/(非常有规律|理性|较为均衡|比较随性)/g, '<span class="highlight">$1</span>')
}

function formatPower(text) {
  if (text === '-') return text
  return text.replace(
    /日均消费([0-9]+)元/g,
    '日均消费<span class="amount">$1</span>元'
  ).replace(
    /，属于(高|中等|理性)消费人群/g,
    '，属于<span class="highlight">$1</span>消费人群'
  )
}

onMounted(() => {
  updateTags()
})

watch(() => props.tags, () => {
  updateTags()
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

/* 消费画像 */
.profile-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.tag-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.tag {
  padding: 6px 12px;
  background: var(--hover-bg);
  color: var(--text-color);
  border-radius: 16px;
  font-size: 13px;
}

.profile-details {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.profile-feature {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: var(--bg-color);
  border-radius: var(--radius-sm);
}

.feature-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 122, 255, 0.1);
  border-radius: 50%;
  color: #007AFF;
}

.feature-title {
  font-size: 12px;
  color: var(--secondary-text);
  margin-bottom: 2px;
}

.feature-description {
  font-size: 14px;
  color: var(--text-color);
  font-weight: 500;
}

.highlight {
  color: var(--primary-color);
  font-weight: 600;
}
</style>
