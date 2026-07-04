<template>
  <!-- 删除区域 -->
  <div class="delete-section">
    <h2 class="section-title">数据管理</h2>
    <div class="delete-area">
      <button class="delete-all-btn" @click="handleClearAllData">
        <i class="fas fa-trash-alt"></i>
        删除所有账单数据
      </button>
      <p class="delete-warning">删除后将清空所有已上传的账单文件和分析数据，此操作不可恢复。</p>
    </div>
  </div>
</template>

<script setup>
import { useUiStore } from '@/stores/ui'
import api from '@/api/client'

const emit = defineEmits(['reload-files'])

const uiStore = useUiStore()

// 清除所有数据
async function handleClearAllData() {
  if (confirm('确定要删除所有账单数据吗？此操作不可恢复！')) {
    try {
      await api.clearData()
      emit('reload-files')
      uiStore.showSuccess('所有数据已清除')
    } catch (error) {
      uiStore.showError('清除失败: ' + error.message)
    }
  }
}
</script>

<style scoped>
/* 删除区域 */
.delete-section {
  background: var(--card-bg);
  border-radius: var(--radius-md);
  padding: 24px;
  margin-top: 24px;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-color);
  margin: 0 0 16px 0;
}

.delete-area {
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: flex-start;
}

.delete-all-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  background: var(--danger-color);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.delete-all-btn:hover {
  background: #E6352A;
}

.delete-warning {
  font-size: 13px;
  color: var(--secondary-text);
  margin: 0;
}
</style>
