<template>
  <div class="settings-page">
    <!-- 页面标题 + 分页签 -->
    <div class="page-header">
      <h1 class="page-title">设置</h1>
      <div class="settings-tabs">
        <button v-for="t in tabs" :key="t.key" class="stab" :class="{ active: tab === t.key }" @click="tab = t.key">
          <i :class="t.icon"></i> {{ t.label }}
        </button>
      </div>
    </div>

    <!-- ============ TAB: 账单文件 ============ -->
    <div v-show="tab === 'files'" class="tab-pane">
      <!-- 成员维度：上传归属 + 成员管理 -->
      <MemberPanel
        :members="members"
        v-model:upload-member="uploadMember"
        @members-changed="reloadMembers"
        @members-changed-with-files="onMembersChangedWithFiles"
      />

      <!-- 双栏布局：支付宝和微信 -->
      <FileUploadPanel
        :alipay-files="alipayFiles"
        :wechat-files="wechatFiles"
        :upload-member="uploadMember"
        @file-uploaded="onFileUploaded"
        @file-deleted="onFileDeleted"
      />

      <!-- 从邮箱导入账单(通用 IMAP) -->
      <MailImportPanel
        :upload-member="uploadMember"
        @reload-files="loadFiles"
      />
    </div><!-- /tab-pane files -->

    <!-- 底部操作栏(仅账单文件页) -->
    <div class="bottom-action-bar" :class="{ visible: tab === 'files' && totalFileCount > 0 }">
      <div class="action-bar-content">
        <div class="file-summary">
          <i class="fas fa-file-alt"></i>
          <span>{{ totalFileCount > 0 ? `已就绪 ${totalFileCount} 个账单文件` : '请上传账单文件' }}</span>
        </div>
        <div class="action-buttons">
          <router-link to="/yearly" class="start-button" :class="{ disabled: totalFileCount === 0 }">
            <i class="fas fa-chart-line"></i>
            开始分析
          </router-link>
        </div>
      </div>
    </div>

    <!-- ============ TAB: AI 与模型 ============ -->
    <div v-show="tab === 'ai'" class="tab-pane">
      <!-- 模型配置(多套档案 + 功能分配) -->
      <AiModelPanel />

      <!-- AI 智能识别账单 -->
      <AiRecognizePanel
        :members="members"
        @reload-files="loadFiles"
      />
    </div><!-- /tab-pane ai -->

    <!-- ============ TAB: 数据管理 ============ -->
    <div v-show="tab === 'data'" class="tab-pane">
      <DataManagePanel @reload-files="loadFiles" />
    </div><!-- /tab-pane data -->

    <!-- ============ TAB: 账号 ============ -->
    <div v-show="tab === 'account'" class="tab-pane">
      <AccountPanel />
    </div><!-- /tab-pane account -->
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useMembersStore } from '@/stores/members'
import api from '@/api/client'
import MemberPanel from '@/components/settings/MemberPanel.vue'
import FileUploadPanel from '@/components/settings/FileUploadPanel.vue'
import MailImportPanel from '@/components/settings/MailImportPanel.vue'
import AiModelPanel from '@/components/settings/AiModelPanel.vue'
import AiRecognizePanel from '@/components/settings/AiRecognizePanel.vue'
import DataManagePanel from '@/components/settings/DataManagePanel.vue'
import AccountPanel from '@/components/settings/AccountPanel.vue'

const membersStore = useMembersStore()

// 成员维度
const members = ref([])
const uploadMember = ref('')   // 本次上传归属的成员

async function reloadMembers() {
  await membersStore.load(true)
  members.value = membersStore.members
  // 当前选中成员不存在(如刚被删)或未设 → 重置为默认成员
  if (!uploadMember.value || !members.value.some(m => m.id === uploadMember.value)) {
    uploadMember.value = membersStore.defaultId()
  }
}

// 删除成员后:成员列表与文件列表都需刷新
async function onMembersChangedWithFiles() {
  await reloadMembers()
  await loadFiles()
}

// ==================== 设置分页签 ====================
const tab = ref('files')
const tabs = [
  { key: 'files', label: '账单文件', icon: 'fas fa-folder-open' },
  { key: 'ai', label: 'AI 与模型', icon: 'fas fa-robot' },
  { key: 'data', label: '数据管理', icon: 'fas fa-database' },
  { key: 'account', label: '账号', icon: 'fas fa-user-shield' },
]

// 文件列表
const alipayFiles = ref([])
const wechatFiles = ref([])

// 总文件数
const totalFileCount = computed(() => alipayFiles.value.length + wechatFiles.value.length)

const route = useRoute()
onMounted(async () => {
  if (['files', 'ai', 'data', 'account'].includes(route.query.tab)) tab.value = route.query.tab
  await reloadMembers()
  await loadFiles()
})

// 加载已上传文件
async function loadFiles() {
  try {
    const data = await api.getFiles()
    console.log('[Settings] Loaded files:', data)

    // 清空现有列表
    alipayFiles.value = []
    wechatFiles.value = []

    // 根据文件来源分类
    data.files.forEach(file => {
      // 使用后端返回的 source 字段判断，如果不存在则回退到扩展名判断
      let isWechat = false
      if (file.source) {
        isWechat = file.source === 'wechat'
      } else {
        isWechat = file.name.endsWith('.xlsx')
      }

      if (isWechat) {
        wechatFiles.value.push(file)
      } else {
        alipayFiles.value.push(file)
      }
    })

    // 排序文件列表
    sortFileList(alipayFiles.value)
    sortFileList(wechatFiles.value)
  } catch (error) {
    console.error('[Settings] 加载文件列表失败:', error)
  }
}

// 排序文件列表
function sortFileList(fileList) {
  fileList.sort((a, b) => {
    return a.name.localeCompare(b.name, 'zh-CN', { numeric: true })
  })
}

// 上传成功:把新文件加入对应列表并排序(与原 handleFiles 内逻辑一致)
function onFileUploaded(newFile) {
  if (newFile.source === 'wechat') {
    wechatFiles.value.push(newFile)
    sortFileList(wechatFiles.value)
  } else {
    alipayFiles.value.push(newFile)
    sortFileList(alipayFiles.value)
  }
}

// 删除成功:从两个列表中移除(与原 deleteFile 内逻辑一致)
function onFileDeleted(filename) {
  alipayFiles.value = alipayFiles.value.filter(f => f.name !== filename)
  wechatFiles.value = wechatFiles.value.filter(f => f.name !== filename)
}
</script>

<style scoped>
/* 基础样式 */
.settings-page {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 20px 140px 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-title {
  font-size: 28px;
  font-weight: 600;
  color: var(--text-color);
  margin: 0;
}

/* 底部操作栏 */
.bottom-action-bar {
  position: fixed;
  bottom: 0;
  left: var(--sidebar-width);
  right: 0;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: saturate(180%) blur(20px);
  border-top: 1px solid var(--border-color);
  padding: 16px 20px;
  transform: translateY(100%);
  transition: transform 0.3s ease;
  z-index: 1000;
}

.bottom-action-bar.visible {
  transform: translateY(0);
}

.action-bar-content {
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.file-summary {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 14px;
  color: var(--text-color);
}

.file-summary i {
  color: var(--primary-color);
}

.start-button {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  background: var(--primary-color);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  text-decoration: none;
  transition: all 0.2s ease;
}

.start-button:hover:not(.disabled) {
  background: #0066E6;
  transform: translateY(-1px);
}

.start-button.disabled {
  opacity: 0.3;
  cursor: not-allowed;
  pointer-events: none;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .bottom-action-bar {
    left: 0;
    padding: 12px 16px;
  }

  .action-bar-content {
    flex-direction: column;
    gap: 12px;
    align-items: stretch;
  }

  .start-button {
    justify-content: center;
  }

  .settings-page {
    padding: 0 16px 140px 16px;
  }

  .page-header {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }
}

/* ===== 设置分页签 ===== */
.settings-tabs { display: flex; gap: 6px; flex-wrap: wrap; }
.stab {
  display: inline-flex; align-items: center; gap: 7px;
  height: 38px; padding: 0 16px; border-radius: 10px; font-size: 14px; cursor: pointer;
  border: 1px solid #e6e6ec; background: #fff; color: #4a4a4f; transition: all .15s;
}
.stab i { font-size: 14px; opacity: .8; }
.stab:hover { border-color: #c9d8ec; color: #007AFF; }
.stab.active { background: #007AFF; border-color: #007AFF; color: #fff; box-shadow: 0 4px 12px rgba(0,122,255,.18); }
.tab-pane { animation: fadeIn .18s ease; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
</style>
