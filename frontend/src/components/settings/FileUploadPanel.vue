<template>
  <!-- 双栏布局：支付宝和微信 -->
  <div class="split-layout">
    <!-- 左侧：支付宝专区 -->
    <div class="provider-column alipay-column">
      <h2 class="column-header">
        <i class="fab fa-alipay"></i> 支付宝账单
      </h2>

      <!-- 支付宝指南 -->
      <div class="upload-guide">
        <h3>如何获取支付宝账单？</h3>
        <ol>
          <li>打开支付宝 App -> 我的 -> 账单</li>
          <li>右上角 ... -> 开具交易流水证明 -> 用于个人对账 -> 申请</li>
          <li>自定义时间范围（最长为一年） -> 填写邮箱 -> 下载账单</li>
          <li>申请记录中找到解压密码 -> 解压下载的文件，获取 CSV 文件</li>
          <li>按年份重命名为【alipay_record_2026.csv】格式</li>
        </ol>
      </div>

      <!-- 支付宝上传区域 -->
      <label
        class="file-upload"
        :class="{ dragover: alipayDragging }"
        @dragover.prevent="alipayDragging = true"
        @dragleave.prevent="alipayDragging = false"
        @drop.prevent="handleAlipayDrop"
      >
        <input
          ref="alipayInput"
          type="file"
          accept=".csv"
          multiple
          @change="handleAlipayFileSelect"
        />
        <div class="upload-icon">
          <i class="fas fa-file-csv"></i>
        </div>
        <div class="upload-text">
          点击或拖拽<br />支付宝 CSV 文件
          <br /><span style="font-size: 12px; opacity: 0.7;">最大 16MB</span>
        </div>
      </label>

      <!-- 支付宝文件列表 -->
      <div class="file-list-container">
        <h4>已上传文件</h4>
        <div class="file-list">
          <div v-for="file in alipayFiles" :key="file.name" class="file-item">
            <i :class="file.name.endsWith('.xlsx') ? 'fas fa-file-excel' : 'fas fa-file-csv'"></i>
            <span class="file-name">{{ file.name }}</span>
            <div class="file-actions">
              <span class="file-status status-success">已上传</span>
              <button class="delete-btn" @click="deleteFile(file.name)">
                <i class="fas fa-trash"></i>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧：微信专区 -->
    <div class="provider-column wechat-column">
      <h2 class="column-header">
        <i class="fab fa-weixin"></i> 微信账单
      </h2>

      <!-- 微信指南 -->
      <div class="upload-guide">
        <h3>如何获取微信账单？</h3>
        <ol>
          <li>打开微信 App -> 我 -> 服务 -> 钱包 -> 账单</li>
          <li>点击右上角 [...] -> 账单下载 -> 用于个人对账</li>
          <li>选择接收方式（微信/邮箱）、账单时间 -> 下一步</li>
          <li><strong>方式一（推荐）：</strong>刷脸验证 -> 微信消息直接下载 XLSX 文件</li>
          <li><strong>方式二：</strong>输入邮箱 -> 刷脸 -> 邮箱接收 (密码在微信消息中)</li>
        </ol>
      </div>

      <!-- 微信上传区域 -->
      <label
        class="file-upload"
        :class="{ dragover: wechatDragging }"
        @dragover.prevent="wechatDragging = true"
        @dragleave.prevent="wechatDragging = false"
        @drop.prevent="handleWechatDrop"
      >
        <input
          ref="wechatInput"
          type="file"
          accept=".xlsx,.csv"
          multiple
          @change="handleWechatFileSelect"
        />
        <div class="upload-icon">
          <i class="fas fa-file-invoice"></i>
        </div>
        <div class="upload-text">
          点击或拖拽<br />微信 XLSX/CSV 文件
          <br /><span style="font-size: 12px; opacity: 0.7;">最大 16MB</span>
        </div>
      </label>

      <!-- 微信文件列表 -->
      <div class="file-list-container">
        <h4>已上传文件</h4>
        <div class="file-list">
          <div v-for="file in wechatFiles" :key="file.name" class="file-item">
            <i :class="file.name.endsWith('.xlsx') ? 'fas fa-file-excel' : 'fas fa-file-csv'"></i>
            <span class="file-name">{{ file.name }}</span>
            <div class="file-actions">
              <span class="file-status status-success">已上传</span>
              <button class="delete-btn" @click="deleteFile(file.name)">
                <i class="fas fa-trash"></i>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useSessionStore } from '@/stores/session'
import { useUiStore } from '@/stores/ui'
import api from '@/api/client'

const props = defineProps({
  alipayFiles: { type: Array, required: true },
  wechatFiles: { type: Array, required: true },
  uploadMember: { type: [String, Number], default: '' },
})
const emit = defineEmits(['file-uploaded', 'file-deleted'])

const sessionStore = useSessionStore()
const uiStore = useUiStore()

// 拖拽状态
const alipayDragging = ref(false)
const wechatDragging = ref(false)

// 文件输入引用
const alipayInput = ref(null)
const wechatInput = ref(null)

// 最大文件大小 16MB
const MAX_FILE_SIZE = 16 * 1024 * 1024

// 检查文件大小
function checkFileSize(file) {
  if (file.size > MAX_FILE_SIZE) {
    uiStore.showError(`文件 ${file.name} 超过大小限制（16MB）`)
    return false
  }
  return true
}

// 检查是否在演示模式
function checkDemoMode() {
  if (sessionStore.isDemo) {
    uiStore.showError('演示模式下无法上传文件，请先退出演示模式')
    return false
  }
  return true
}

// 处理支付宝文件选择
async function handleAlipayFileSelect(event) {
  const files = Array.from(event.target.files)
  if (files.length > 0) {
    await handleFiles(files, '.csv', 'alipay')
  }
  // 重置 input
  event.target.value = ''
}

// 处理微信文件选择
async function handleWechatFileSelect(event) {
  const files = Array.from(event.target.files)
  if (files.length > 0) {
    await handleFiles(files, '.xlsx,.csv', 'wechat')
  }
  // 重置 input
  event.target.value = ''
}

// 处理支付宝拖放
async function handleAlipayDrop(event) {
  alipayDragging.value = false
  const files = Array.from(event.dataTransfer.files).filter(file =>
    file.name.toLowerCase().endsWith('.csv')
  )
  if (files.length > 0) {
    await handleFiles(files, '.csv', 'alipay')
  }
}

// 处理微信拖放
async function handleWechatDrop(event) {
  wechatDragging.value = false
  const files = Array.from(event.dataTransfer.files).filter(file =>
    file.name.toLowerCase().endsWith('.xlsx') || file.name.toLowerCase().endsWith('.csv')
  )
  if (files.length > 0) {
    await handleFiles(files, '.xlsx,.csv', 'wechat')
  }
}

// 处理文件上传
async function handleFiles(files, allowedExt, provider) {
  if (!checkDemoMode()) return

  const allowedExtensions = allowedExt.split(',').map(e => e.trim().toLowerCase())

  for (const file of files) {
    const fileName = file.name.toLowerCase()
    const isAllowed = allowedExtensions.some(ext => fileName.endsWith(ext))

    if (!isAllowed) {
      uiStore.showError(`请上传 ${allowedExt} 格式的文件`)
      continue
    }

    if (!checkFileSize(file)) continue

    try {
      uiStore.setGlobalLoading(true)
      const formData = new FormData()
      formData.append('file', file)
      if (props.uploadMember) formData.append('member_id', props.uploadMember)

      const result = await api.uploadFile(formData)

      // 通知父组件把新文件加入对应列表并排序(与原逻辑一致:按上传归属列分类)
      emit('file-uploaded', { name: result.filename || file.name, source: provider })

      uiStore.showSuccess('文件上传成功')
    } catch (error) {
      uiStore.showError('上传失败: ' + error.message)
    } finally {
      uiStore.setGlobalLoading(false)
    }
  }
}

// 删除文件
async function deleteFile(filename) {
  if (confirm(`确定要删除文件 "${filename}" 吗？`)) {
    try {
      await api.deleteFile(filename)
      // 通知父组件从列表中移除(与原逻辑一致)
      emit('file-deleted', filename)
      uiStore.showSuccess('文件已删除')
    } catch (error) {
      uiStore.showError('删除失败: ' + error.message)
    }
  }
}
</script>

<style scoped>
/* 双栏布局 */
.split-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  margin-bottom: 24px;
}

.provider-column {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
  border: 1px solid rgba(0, 0, 0, 0.04);
  transition: all 0.3s ease;
}

.provider-column:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.06);
}

.column-header {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-color);
  margin: 0 0 20px 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.column-header i {
  font-size: 20px;
}

.alipay-column .column-header i {
  color: #00A0E9;
}

.wechat-column .column-header i {
  color: #07C160;
}

/* 上传指南 */
.upload-guide {
  background: #fbfbfd;
  border-radius: 10px;
  padding: 16px;
  margin-bottom: 24px;
  border: 1px solid rgba(0, 0, 0, 0.03);
}

.upload-guide h3 {
  font-size: 14px;
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 12px;
  margin-top: 0;
}

.upload-guide ol {
  margin: 0;
  padding-left: 20px;
}

.upload-guide li {
  font-size: 13px;
  line-height: 1.6;
  color: #424245;
  margin-bottom: 8px;
}

.upload-guide li strong {
  color: #1d1d1f;
  font-weight: 600;
}

/* 文件上传区域 */
.file-upload {
  display: block;
  border: 2px dashed #d2d2d7;
  background: #fafafc;
  border-radius: 12px;
  padding: 32px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s ease;
  height: 180px;
}

.file-upload:hover,
.file-upload.dragover {
  border-color: #007aff;
  background: #f0f8ff;
  transform: scale(1.02);
}

.file-upload input[type="file"] {
  display: none;
}

.upload-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.upload-icon i {
  color: #86868b;
  transition: color 0.2s ease;
}

.file-upload:hover .upload-icon i {
  color: #007aff;
  transform: scale(1.1);
}

.upload-text {
  color: #86868b;
  font-size: 14px;
  font-weight: 500;
}

/* 文件列表 */
.file-list-container {
  margin-top: 24px;
}

.file-list-container h4 {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-color);
  margin: 0 0 12px 0;
}

.file-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: var(--bg-color);
  border-radius: var(--radius-sm);
  transition: background-color 0.2s;
}

.file-item:hover {
  background: var(--hover-bg);
}

.file-item > i {
  color: var(--primary-color);
  font-size: 18px;
}

.file-name {
  flex: 1;
  font-size: 13px;
  color: var(--text-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-status {
  font-size: 12px;
  color: var(--secondary-text);
}

.file-status.status-success {
  color: #34C759;
}

.delete-btn {
  background: none;
  border: none;
  padding: 6px;
  cursor: pointer;
  color: var(--secondary-text);
  border-radius: var(--radius-sm);
  transition: all 0.2s;
}

.delete-btn:hover {
  color: var(--danger-color);
  background: rgba(255, 59, 48, 0.1);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .split-layout {
    grid-template-columns: 1fr;
  }
}
</style>
