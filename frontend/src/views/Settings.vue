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
    <div class="member-panel">
      <div class="member-row">
        <label><i class="fas fa-user-tag"></i> 本次上传归属成员：</label>
        <select v-model="uploadMember" class="member-select">
          <option v-for="m in members" :key="m.id" :value="m.id">{{ m.name }}</option>
        </select>
        <span class="member-tip">上传的账单会整份记到该成员名下（每份导出对应一个人的账户）</span>
      </div>
      <div class="member-row">
        <label>成员：</label>
        <span v-for="m in members" :key="m.id" class="member-chip" :style="{ borderColor: m.color }">
          <span class="dot" :style="{ background: m.color }"></span>{{ m.name }}
          <i v-if="!m.is_self" class="fas fa-times del" @click="deleteMember(m)"></i>
        </span>
        <input v-model="newMemberName" class="member-add-input" placeholder="新增成员名" @keyup.enter="addMember" />
        <button class="member-add-btn" @click="addMember">+ 添加</button>
      </div>
    </div>

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
    <div class="ai-section">
      <h2 class="section-title"><i class="fas fa-sliders-h title-icon ai-color"></i> 模型配置</h2>
      <div class="ai-card">
        <p class="ai-desc">
          接入任意 <strong>Anthropic 兼容</strong>(/v1/messages)的大模型。可建<strong>多套配置</strong>,
          并为不同功能(对话 / 账单识别 / 智能分析)分别指定 —— 识别类多模态任务可单独用支持图片的模型。
          配置只存在<strong>你自己的账号</strong>里,后台只留掩码,不持有任何人的明文 Key。
        </p>

        <!-- 档案列表 -->
        <div class="profile-list">
          <div v-for="p in aiConfig.profiles" :key="p.id" class="profile-card" :class="{ def: p.id === aiConfig.default_profile }">
            <div class="profile-main">
              <div class="profile-name">
                {{ p.name }}
                <span v-if="p.id === aiConfig.default_profile" class="tag def-tag">默认</span>
                <span v-if="!p.has_key" class="tag nokey-tag">未填 Key</span>
              </div>
              <div class="profile-meta">
                <i class="fas fa-microchip"></i> {{ p.model || '未指定模型' }}
                <span class="dot-sep">·</span> {{ hostOf(p.base_url) }}
                <span class="dot-sep">·</span> Key {{ p.has_key ? p.api_key_masked : '—' }}
              </div>
              <div v-if="usedBy(p.id).length" class="profile-uses">
                <span v-for="u in usedBy(p.id)" :key="u" class="use-chip">{{ u }}</span>
              </div>
            </div>
            <div class="profile-acts">
              <button class="mini-btn" @click="testProfile(p)" :disabled="!!aiBusy"><i class="fas fa-plug"></i> 测试</button>
              <button class="mini-btn" @click="editProfile(p)"><i class="fas fa-pen"></i> 编辑</button>
              <button class="mini-btn" v-if="p.id !== aiConfig.default_profile" @click="setDefault(p)"><i class="fas fa-star"></i> 设默认</button>
              <button class="mini-btn danger" @click="removeProfile(p)"><i class="fas fa-trash"></i></button>
            </div>
            <span v-if="testFor === p.id" class="test-result" :class="{ ok: testOk }">
              <i :class="testOk ? 'fas fa-circle-check' : 'fas fa-circle-xmark'"></i> {{ testMsg }}
            </span>
          </div>
          <button v-if="!editing" class="add-profile" @click="newProfile"><i class="fas fa-plus"></i> 新增模型配置</button>
        </div>

        <!-- 档案编辑器(新增/编辑) -->
        <div v-if="editing" class="profile-editor">
          <div class="editor-title">{{ editing.id ? '编辑模型配置' : '新增模型配置' }}</div>
          <div class="provider-row">
            <button
              v-for="p in builtinProviders" :key="p.name"
              class="provider-chip" :class="{ active: editing.base_url === p.base_url }"
              @click="applyTemplate(p)"
            >{{ p.name }}</button>
          </div>
          <div class="cfg-grid">
            <div class="cfg-field">
              <label>配置名称</label>
              <input v-model.trim="editing.name" placeholder="如 Kimi 对话 / GLM 多模态" maxlength="24" />
            </div>
            <div class="cfg-field">
              <label>模型 Model <span class="muted" v-if="modelSuggestions.length">(可下拉常用)</span></label>
              <input v-model.trim="editing.model" list="model-suggestions" placeholder="如 kimi-k2.5" />
              <datalist id="model-suggestions">
                <option v-for="m in modelSuggestions" :key="m" :value="m" />
              </datalist>
            </div>
            <div class="cfg-field full">
              <label>服务地址 Base URL</label>
              <input v-model.trim="editing.base_url" placeholder="选择上方供应商或手动输入 https://..." />
            </div>
            <div class="cfg-field full">
              <label>API Key <span class="muted" v-if="editing.id">(留空=不修改已保存的 Key)</span></label>
              <input v-model="editing.api_key" type="password" placeholder="sk-..." autocomplete="off" />
            </div>
          </div>
          <div class="cfg-actions">
            <button class="test-btn" @click="testEditing" :disabled="!!aiBusy">
              <i class="fas fa-plug"></i> {{ aiBusy === 'test' && testFor === 'editor' ? '测试中…' : '测试连接' }}
            </button>
            <button class="save-btn" @click="saveProfile" :disabled="!!aiBusy"><i class="fas fa-check"></i> 保存</button>
            <button class="reset-btn" @click="editing = null">取消</button>
            <span v-if="testFor === 'editor'" class="test-result" :class="{ ok: testOk }">
              <i :class="testOk ? 'fas fa-circle-check' : 'fas fa-circle-xmark'"></i> {{ testMsg }}
            </span>
          </div>
        </div>

        <!-- 功能分配 -->
        <div v-if="aiConfig.profiles.length" class="routing">
          <h3 class="routing-title"><i class="fas fa-shuffle"></i> 功能使用哪套配置</h3>
          <div class="route-grid">
            <div class="route-row">
              <label>默认配置</label>
              <select v-model="routingDefault" @change="saveRouting">
                <option v-for="p in aiConfig.profiles" :key="p.id" :value="p.id">{{ p.name }}</option>
              </select>
            </div>
            <div class="route-row" v-for="pp in aiConfig.purposes" :key="pp.key">
              <label>{{ pp.label }}</label>
              <select v-model="routing[pp.key]" @change="saveRouting">
                <option value="">跟随默认</option>
                <option v-for="p in aiConfig.profiles" :key="p.id" :value="p.id">{{ p.name }}</option>
              </select>
            </div>
            <div class="route-row switch-row">
              <label>每月自动智能分析</label>
              <label class="switch">
                <input type="checkbox" v-model="autoAnalyze" @change="saveRouting" />
                <span class="slider"></span>
              </label>
              <span class="muted">每月 1 号起,打开各分析页自动生成本期 AI 洞察</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- AI 智能识别账单 -->
    <div class="ai-section">
      <h2 class="section-title"><i class="fas fa-wand-magic-sparkles title-icon ai-color"></i> AI 智能识别账单</h2>
      <div class="ai-card">
        <p class="ai-desc">不是支付宝/微信/银行标准格式的账单?把<strong>文件或文字</strong>交给 AI,自动提取成交易记录后导入。</p>

        <div class="rec-grid">
          <!-- 文件投放区 -->
          <label
            class="rec-drop" :class="{ dragging: recDragging, hasfile: !!recFileName }"
            @dragover.prevent="recDragging = true" @dragleave.prevent="recDragging = false"
            @drop.prevent="onRecDrop"
          >
            <input ref="recFileInput" type="file" accept=".csv,.txt,.xlsx,.pdf" hidden @change="onRecPick" />
            <i :class="recFileName ? 'fas fa-file-circle-check' : 'fas fa-cloud-arrow-up'"></i>
            <span v-if="recFileName" class="rec-filename">{{ recFileName }}</span>
            <span v-else>点击或拖入文件<br /><em>csv / txt / xlsx / pdf</em></span>
            <button v-if="recFileName" class="rec-clear" @click.prevent="clearRecFile">×</button>
          </label>
          <!-- 文本粘贴区 -->
          <textarea v-model="recText" class="rec-textarea" placeholder="或者直接把账单文字粘贴到这里…&#10;例:5月20日 星巴克 拿铁 35元 微信支付"></textarea>
        </div>

        <div class="cfg-actions">
          <button class="save-btn" @click="doRecognize" :disabled="recLoading">
            <i class="fas fa-wand-magic-sparkles"></i> {{ recLoading ? 'AI 识别中…' : '开始识别' }}
          </button>
          <span v-if="recLoading" class="muted">大段内容可能需要十几秒</span>
        </div>

        <!-- 识别结果预览 -->
        <div v-if="recRows.length" class="rec-result">
          <div class="rec-result-head">
            <span class="rec-count"><i class="fas fa-list-check"></i> 识别到 {{ recRows.length }} 笔</span>
            <div class="rec-import">
              <select v-model="recMember" class="member-select">
                <option v-for="m in members" :key="m.id" :value="m.id">归属:{{ m.name }}</option>
              </select>
              <button class="save-btn" @click="doImport" :disabled="recLoading">
                <i class="fas fa-file-import"></i> 导入到账单
              </button>
            </div>
          </div>
          <div class="rec-table-wrap">
            <table class="rec-table">
              <thead><tr><th>时间</th><th>分类</th><th>对方</th><th>说明</th><th>收支</th><th class="num">金额</th><th></th></tr></thead>
              <tbody>
                <tr v-for="(r, i) in recRows" :key="i">
                  <td>{{ r['交易时间'] }}</td>
                  <td>{{ r['交易分类'] }}</td>
                  <td>{{ r['交易对方'] }}</td>
                  <td class="desc">{{ r['商品说明'] }}</td>
                  <td><span class="type-tag" :class="typeClass(r['收/支'])">{{ r['收/支'] }}</span></td>
                  <td class="num">{{ Number(r['金额']).toFixed(2) }}</td>
                  <td><button class="row-del" @click="recRows.splice(i, 1)" title="移除此行">×</button></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    </div><!-- /tab-pane ai -->

    <!-- ============ TAB: 数据管理 ============ -->
    <div v-show="tab === 'data'" class="tab-pane">
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
    </div><!-- /tab-pane data -->
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useSessionStore } from '@/stores/session'
import { useUiStore } from '@/stores/ui'
import { useMembersStore } from '@/stores/members'
import api from '@/api/client'

const sessionStore = useSessionStore()
const uiStore = useUiStore()
const membersStore = useMembersStore()

// 成员维度
const members = ref([])
const uploadMember = ref('')   // 本次上传归属的成员
const newMemberName = ref('')

async function reloadMembers() {
  await membersStore.load(true)
  members.value = membersStore.members
  // 当前选中成员不存在(如刚被删)或未设 → 重置为默认成员
  if (!uploadMember.value || !members.value.some(m => m.id === uploadMember.value)) {
    uploadMember.value = membersStore.defaultId()
  }
}

async function addMember() {
  const name = newMemberName.value.trim()
  if (!name) return
  try {
    await membersStore.add(name)
    newMemberName.value = ''
    await reloadMembers()
    uiStore.showSuccess('成员已添加')
  } catch (e) { uiStore.showError('添加失败: ' + e.message) }
}

async function deleteMember(m) {
  if (m.is_self) { uiStore.showError('不能删除「本人」'); return }
  if (!confirm(`删除成员「${m.name}」？其名下账单会回落到默认成员。`)) return
  try {
    await membersStore.remove(m.id)
    await reloadMembers()
    await loadFiles()
    uiStore.showSuccess('成员已删除')
  } catch (e) { uiStore.showError('删除失败: ' + e.message) }
}

// ==================== 设置分页签 ====================
const tab = ref('files')
const tabs = [
  { key: 'files', label: '账单文件', icon: 'fas fa-folder-open' },
  { key: 'ai', label: 'AI 与模型', icon: 'fas fa-robot' },
  { key: 'data', label: '数据管理', icon: 'fas fa-database' },
]

// ==================== AI 模型配置(多档案 + 功能分配) ====================
const aiConfig = ref({ profiles: [], assignments: {}, default_profile: '', custom_providers: [], auto_analyze: true, purposes: [], has_default: false })
const editing = ref(null)           // 正在新增/编辑的档案 {id?, name, base_url, model, api_key}
const aiBusy = ref('')
const testFor = ref('')             // 'editor' 或某档案 id
const testMsg = ref('')
const testOk = ref(false)
const routing = ref({})             // assignments 本地副本
const routingDefault = ref('')
const autoAnalyze = ref(true)

// Anthropic 兼容服务商预设(2026-06 各家最新模型;含多模态识别可用模型)
const builtinProviders = [
  { name: 'Kimi 会员版', base_url: 'https://api.kimi.com/coding/', model: 'kimi-k2.5',
    models: ['kimi-k2.5', 'kimi-k2-thinking', 'kimi-latest', 'kimi-k2-0905-preview'] },
  { name: 'Kimi 开放平台', base_url: 'https://api.moonshot.cn/anthropic', model: 'kimi-k2.5',
    models: ['kimi-k2.5', 'kimi-k2-thinking', 'kimi-latest'] },
  { name: 'DeepSeek', base_url: 'https://api.deepseek.com/anthropic', model: 'deepseek-chat',
    models: ['deepseek-chat', 'deepseek-reasoner'] },
  { name: '智谱 GLM', base_url: 'https://open.bigmodel.cn/api/anthropic', model: 'glm-5.1',
    models: ['glm-5.1', 'glm-5', 'glm-4.6', 'glm-4.6v'] },
  { name: '通义千问', base_url: 'https://dashscope.aliyuncs.com/apps/anthropic', model: 'qwen3.6-plus',
    models: ['qwen3.6-plus', 'qwen3-max', 'qwen3-vl-plus', 'qwen3-coder-plus'] },
  { name: 'MiniMax', base_url: 'https://api.minimaxi.com/anthropic', model: 'minimax-m2.7',
    models: ['minimax-m2.7', 'MiniMax-M2'] },
  { name: 'Claude 官方', base_url: 'https://api.anthropic.com', model: 'claude-sonnet-4-6',
    models: ['claude-opus-4-8', 'claude-sonnet-4-6', 'claude-haiku-4-5'] },
  { name: 'OpenRouter', base_url: 'https://openrouter.ai/api', model: 'anthropic/claude-sonnet-4.6',
    models: ['anthropic/claude-sonnet-4.6', 'anthropic/claude-opus-4.8', 'moonshotai/kimi-k2.5', 'google/gemini-2.5-pro'] },
  { name: 'SiliconFlow', base_url: 'https://api.siliconflow.cn', model: 'deepseek-ai/DeepSeek-V3.2',
    models: ['deepseek-ai/DeepSeek-V3.2', 'Qwen/Qwen3-Max', 'moonshotai/Kimi-K2.5'] },
  { name: 'Ollama 本地', base_url: 'http://localhost:11434', model: 'qwen3-coder',
    models: ['qwen3-coder', 'deepseek-r1', 'llama4', 'qwen2.5vl'] }
]

function hostOf(url) {
  try { return new URL(url).host } catch { return url || '—' }
}
const purposeLabel = (k) => (aiConfig.value.purposes.find(p => p.key === k) || {}).label || k
function usedBy(pid) {
  const out = []
  const a = aiConfig.value.assignments || {}
  for (const k of Object.keys(a)) {
    if (a[k] === pid) out.push(purposeLabel(k))
  }
  return out
}

// 编辑器里 base_url 命中的预设 → 模型联想
const modelSuggestions = computed(() => {
  const hit = builtinProviders.find(p => p.base_url === (editing.value && editing.value.base_url))
  return hit ? (hit.models || [hit.model]) : []
})

function newProfile() {
  editing.value = { name: '', base_url: '', model: '', api_key: '' }
  testFor.value = ''
}
function editProfile(p) {
  editing.value = { id: p.id, name: p.name, base_url: p.base_url, model: p.model, api_key: '' }
  testFor.value = ''
}
function applyTemplate(t) {
  if (!editing.value) return
  editing.value.base_url = t.base_url
  editing.value.model = t.model || ''
  if (!editing.value.name) editing.value.name = t.name
  testFor.value = ''
}

function syncRouting() {
  routing.value = { ...(aiConfig.value.assignments || {}) }
  routingDefault.value = aiConfig.value.default_profile || ''
  autoAnalyze.value = aiConfig.value.auto_analyze !== false
}

async function loadAiConfig() {
  try {
    const r = await api.aiGetConfig()
    aiConfig.value = r.config
    syncRouting()
  } catch (e) { /* 未登录等场景忽略 */ }
}

async function saveProfile() {
  const e = editing.value
  if (!e || !(e.name || '').trim()) { uiStore.showError('请填写配置名称'); return }
  aiBusy.value = 'save'
  try {
    const payload = { name: e.name.trim(), base_url: (e.base_url || '').trim(), model: (e.model || '').trim() }
    if (e.id) payload.id = e.id
    if (!e.id || e.api_key) payload.api_key = e.api_key || ''   // 新建必带;编辑仅在填了时改
    const r = await api.aiUpsertProfile(payload)
    aiConfig.value = r.config; syncRouting()
    editing.value = null
    uiStore.showSuccess('模型配置已保存')
  } catch (err) { uiStore.showError('保存失败: ' + err.message) }
  finally { aiBusy.value = '' }
}

async function removeProfile(p) {
  if (!confirm(`删除模型配置「${p.name}」?`)) return
  try {
    const r = await api.aiDeleteProfile(p.id)
    aiConfig.value = r.config; syncRouting()
    uiStore.showSuccess('已删除')
  } catch (e) { uiStore.showError('删除失败: ' + e.message) }
}

async function setDefault(p) {
  routingDefault.value = p.id
  await saveRouting()
}

async function saveRouting() {
  try {
    const r = await api.aiSaveRouting({
      assignments: routing.value,
      default_profile: routingDefault.value,
      auto_analyze: autoAnalyze.value,
      custom_providers: aiConfig.value.custom_providers || []
    })
    aiConfig.value = r.config; syncRouting()
  } catch (e) { uiStore.showError('保存失败: ' + e.message) }
}

async function testProfile(p) {
  aiBusy.value = 'test'; testFor.value = p.id; testMsg.value = '测试中…'; testOk.value = false
  try {
    const r = await api.aiTestConfig({ id: p.id })
    testOk.value = r.ok; testMsg.value = r.message
  } catch (e) { testOk.value = false; testMsg.value = e.message || '测试失败' }
  finally { aiBusy.value = '' }
}

async function testEditing() {
  const e = editing.value; if (!e) return
  aiBusy.value = 'test'; testFor.value = 'editor'; testMsg.value = '测试中…'; testOk.value = false
  try {
    const payload = { base_url: e.base_url, model: e.model }
    if (e.id) payload.id = e.id
    if (e.api_key) payload.api_key = e.api_key
    const r = await api.aiTestConfig(payload)
    testOk.value = r.ok; testMsg.value = r.message
  } catch (err) { testOk.value = false; testMsg.value = err.message || '测试失败' }
  finally { aiBusy.value = '' }
}

// ==================== AI 智能识别账单 ====================
const recText = ref('')
const recFileInput = ref(null)
const recFileName = ref('')
const recFile = ref(null)
const recDragging = ref(false)
const recRows = ref([])
const recLoading = ref(false)
const recMember = ref('')

function onRecPick(e) {
  const f = e.target.files && e.target.files[0]
  if (f) { recFile.value = f; recFileName.value = f.name }
}

function onRecDrop(e) {
  recDragging.value = false
  const f = e.dataTransfer.files && e.dataTransfer.files[0]
  if (f) { recFile.value = f; recFileName.value = f.name }
}

function clearRecFile() {
  recFile.value = null
  recFileName.value = ''
  if (recFileInput.value) recFileInput.value.value = ''
}

function typeClass(t) {
  return { 收入: 'in', 支出: 'out', 转入: 'tin', 转出: 'tout' }[t] || 'neutral'
}

async function doRecognize() {
  if (!recFile.value && !recText.value.trim()) { uiStore.showError('请选择文件或粘贴文字'); return }
  recLoading.value = true
  recRows.value = []
  try {
    let r
    if (recFile.value) {
      const fd = new FormData()
      fd.append('file', recFile.value)
      r = await api.aiRecognize(fd)
    } else {
      r = await api.aiRecognizeText(recText.value, '')
    }
    recRows.value = r.rows || []
    if (!recRows.value.length) uiStore.showError('未能识别出交易记录,可能是扫描件或内容无交易信息')
    if (!recMember.value) recMember.value = membersStore.defaultId()
  } catch (e) { uiStore.showError('识别失败: ' + (e.message || '')) }
  finally { recLoading.value = false }
}

async function doImport() {
  if (!recRows.value.length) return
  recLoading.value = true
  try {
    const r = await api.aiRecognizeImport(recRows.value, recMember.value || membersStore.defaultId(), 'AI识别账单')
    uiStore.showSuccess(`已导入 ${r.count} 笔`)
    recRows.value = []
    recText.value = ''
    clearRecFile()
    await loadFiles()
  } catch (e) { uiStore.showError('导入失败: ' + (e.message || '')) }
  finally { recLoading.value = false }
}

// 文件列表
const alipayFiles = ref([])
const wechatFiles = ref([])

// 拖拽状态
const alipayDragging = ref(false)
const wechatDragging = ref(false)

// 文件输入引用
const alipayInput = ref(null)
const wechatInput = ref(null)

// 总文件数
const totalFileCount = computed(() => alipayFiles.value.length + wechatFiles.value.length)

// 最大文件大小 16MB
const MAX_FILE_SIZE = 16 * 1024 * 1024

const route = useRoute()
onMounted(async () => {
  if (['files', 'ai', 'data'].includes(route.query.tab)) tab.value = route.query.tab
  await reloadMembers()
  await loadFiles()
  await loadAiConfig()
  recMember.value = membersStore.defaultId()
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
      if (uploadMember.value) formData.append('member_id', uploadMember.value)

      const result = await api.uploadFile(formData)

      // 添加到对应的文件列表
      const newFile = { name: result.filename || file.name, source: provider }
      if (provider === 'wechat') {
        wechatFiles.value.push(newFile)
        sortFileList(wechatFiles.value)
      } else {
        alipayFiles.value.push(newFile)
        sortFileList(alipayFiles.value)
      }

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

      // 从列表中移除
      alipayFiles.value = alipayFiles.value.filter(f => f.name !== filename)
      wechatFiles.value = wechatFiles.value.filter(f => f.name !== filename)

      uiStore.showSuccess('文件已删除')
    } catch (error) {
      uiStore.showError('删除失败: ' + error.message)
    }
  }
}

// 清除所有数据
async function handleClearAllData() {
  if (confirm('确定要删除所有账单数据吗？此操作不可恢复！')) {
    try {
      await api.clearData()

      // 清空文件列表
      alipayFiles.value = []
      wechatFiles.value = []

      uiStore.showSuccess('所有数据已清除')
    } catch (error) {
      uiStore.showError('清除失败: ' + error.message)
    }
  }
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

/* 响应式设计 */
@media (max-width: 768px) {
  .split-layout {
    grid-template-columns: 1fr;
  }

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
</style>

<style scoped>
/* 成员维度面板 */
.member-panel {
  background: var(--card-bg, #fff);
  border: 1px solid var(--border-color, #eee);
  border-radius: 14px;
  padding: 16px 18px;
  margin-bottom: 18px;
}
.member-row { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; }
.member-row + .member-row { margin-top: 12px; }
.member-row > label { font-size: 14px; color: var(--text-color, #333); font-weight: 500; }
.member-select { height: 34px; border: 1px solid #d2d2d7; border-radius: 8px; padding: 0 12px; font-size: 14px; }
.member-tip { font-size: 12px; color: #9aa0a6; }
.member-chip {
  display: inline-flex; align-items: center; gap: 6px;
  border: 1px solid #d2d2d7; border-radius: 16px; padding: 4px 12px; font-size: 13px;
}
.member-chip .dot { width: 8px; height: 8px; border-radius: 50%; }
.member-chip .del { color: #c0c0c0; cursor: pointer; margin-left: 2px; }
.member-chip .del:hover { color: #ff3b30; }
.member-add-input { height: 32px; border: 1px solid #d2d2d7; border-radius: 8px; padding: 0 10px; font-size: 13px; width: 120px; }
.member-add-btn { height: 32px; padding: 0 14px; border: none; border-radius: 8px; background: #007AFF; color: #fff; cursor: pointer; font-size: 13px; }

/* ===== AI 配置 / 智能识别 区块 ===== */
.ai-section { margin: 26px 0; }
.ai-section .section-title { display: flex; align-items: center; gap: 8px; font-size: 17px; margin-bottom: 12px; }
.title-icon.ai-color { color: #AF52DE; }
.ai-card {
  background: var(--card-bg, #fff); border: 1px solid #ebebf0; border-radius: 16px;
  padding: 20px 22px; box-shadow: 0 2px 10px rgba(0,0,0,.03);
}
.ai-desc { color: #6e6e73; font-size: 13px; margin: 0 0 14px; line-height: 1.7; }
.cfg-badge { display: inline-block; font-size: 11px; border-radius: 8px; padding: 2px 8px; margin-left: 8px; }
.cfg-badge.default { background: #eef1f4; color: #6e6e73; }
.cfg-badge.custom { background: #e6f6ec; color: #1d8a44; }
.muted { color: #9aa0a6; font-size: 12px; font-weight: normal; }

.provider-row { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
.provider-chip {
  border: 1px solid #e2e2e8; background: #fff; color: #3a3a3c;
  padding: 6px 14px; border-radius: 16px; font-size: 13px; cursor: pointer; transition: all .15s;
}
.provider-chip:hover { border-color: #007AFF; color: #007AFF; }
.provider-chip.active { background: #eaf3ff; border-color: #007AFF; color: #007AFF; font-weight: 500; }
.custom-chip { display: inline-flex; align-items: center; gap: 7px; border-style: dashed; }
.chip-del { color: #c0c0c0; font-size: 11px; cursor: pointer; }
.chip-del:hover { color: #ff3b30; }
.add-chip { color: #007AFF; border-style: dashed; }
.add-provider {
  display: flex; flex-wrap: wrap; gap: 10px; align-items: center;
  background: #f7f9fc; border: 1px dashed #c9d8ec; border-radius: 12px;
  padding: 12px 14px; margin-bottom: 14px;
}
.add-provider input {
  height: 36px; border: 1px solid #e2e2e8; border-radius: 9px; padding: 0 11px;
  font-size: 13px; outline: none; flex: 1; min-width: 140px;
}
.add-provider input:focus { border-color: #007AFF; }
.add-provider .ap-url { flex: 2; min-width: 220px; }

.cfg-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px 16px; }
.cfg-field { display: flex; flex-direction: column; }
.cfg-field.full { grid-column: 1 / -1; }
.cfg-field label { font-size: 12.5px; color: #6e6e73; margin-bottom: 6px; }
.cfg-field input {
  height: 40px; border: 1px solid #e2e2e8; border-radius: 10px; padding: 0 13px;
  font-size: 13.5px; outline: none; transition: all .15s; background: #fff;
}
.cfg-field input:focus { border-color: #007AFF; box-shadow: 0 0 0 3px rgba(0,122,255,.08); }

.cfg-actions { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; margin-top: 16px; }
.test-btn, .save-btn, .reset-btn {
  display: inline-flex; align-items: center; gap: 7px;
  height: 38px; padding: 0 18px; border-radius: 10px; font-size: 13.5px; cursor: pointer;
  border: none; transition: all .15s;
}
.test-btn { background: #fff; border: 1px solid #d8d8de; color: #3a3a3c; }
.test-btn:hover { border-color: #AF52DE; color: #AF52DE; }
.save-btn { background: #007AFF; color: #fff; }
.save-btn:hover { background: #0a6ee0; }
.save-btn:disabled, .test-btn:disabled { opacity: .55; cursor: not-allowed; }
.reset-btn { background: none; color: #9aa0a6; text-decoration: underline; padding: 0 6px; }
.test-result { font-size: 12.5px; color: #c0392b; display: inline-flex; align-items: center; gap: 5px; }
.test-result.ok { color: #1d8a44; }

/* 识别区 */
.rec-grid { display: grid; grid-template-columns: 240px 1fr; gap: 14px; }
@media (max-width: 760px) { .rec-grid { grid-template-columns: 1fr; } .cfg-grid { grid-template-columns: 1fr; } }
.rec-drop {
  position: relative; display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 8px; min-height: 130px; border: 1.5px dashed #cfd3da; border-radius: 14px;
  background: #fafbfc; color: #86868b; font-size: 13px; text-align: center; cursor: pointer;
  transition: all .15s; padding: 12px;
}
.rec-drop:hover, .rec-drop.dragging { border-color: #007AFF; background: #f2f8ff; color: #007AFF; }
.rec-drop.hasfile { border-style: solid; border-color: #34C759; background: #f3fbf5; color: #1d8a44; }
.rec-drop i { font-size: 26px; }
.rec-drop em { font-style: normal; font-size: 11px; color: #b3b8bf; }
.rec-filename { font-size: 12.5px; word-break: break-all; max-width: 100%; }
.rec-clear {
  position: absolute; top: 8px; right: 10px; border: none; background: none;
  color: #b3b8bf; font-size: 16px; cursor: pointer;
}
.rec-clear:hover { color: #ff3b30; }
.rec-textarea {
  min-height: 130px; border: 1px solid #e2e2e8; border-radius: 14px; padding: 12px 14px;
  font-size: 13px; line-height: 1.6; resize: vertical; outline: none; transition: all .15s;
}
.rec-textarea:focus { border-color: #007AFF; box-shadow: 0 0 0 3px rgba(0,122,255,.08); }

.rec-result { margin-top: 18px; }
.rec-result-head { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; margin-bottom: 10px; }
.rec-count { font-size: 14px; color: #1d1d1f; font-weight: 500; }
.rec-count i { color: #34C759; margin-right: 5px; }
.rec-import { display: flex; align-items: center; gap: 10px; }
.rec-table-wrap { border: 1px solid #ebebf0; border-radius: 12px; overflow: auto; max-height: 380px; }
.rec-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.rec-table th {
  position: sticky; top: 0; background: #f6f8fa; color: #6e6e73; font-weight: 500;
  text-align: left; padding: 9px 12px; border-bottom: 1px solid #ebebf0; white-space: nowrap;
}
.rec-table td { padding: 8px 12px; border-bottom: 1px solid #f4f4f6; }
.rec-table tr:last-child td { border-bottom: none; }
.rec-table td.desc { max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rec-table .num { text-align: right; font-variant-numeric: tabular-nums; }
.type-tag { font-size: 11px; border-radius: 6px; padding: 2px 8px; white-space: nowrap; }
.type-tag.in { background: #e6f6ec; color: #1d8a44; }
.type-tag.out { background: #feeeec; color: #d04437; }
.type-tag.tin { background: #e8f1ff; color: #0a59c9; }
.type-tag.tout { background: #fff4e5; color: #b46408; }
.type-tag.neutral { background: #eef1f4; color: #6e6e73; }
.row-del { border: none; background: none; color: #c9ced6; cursor: pointer; font-size: 14px; }
.row-del:hover { color: #ff3b30; }
</style>

<style scoped>
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

/* ===== 模型配置:档案列表 ===== */
.profile-list { display: flex; flex-direction: column; gap: 10px; margin-bottom: 18px; }
.profile-card {
  position: relative; display: flex; align-items: center; gap: 14px; flex-wrap: wrap;
  border: 1px solid #ebebf0; border-radius: 14px; padding: 14px 16px; background: #fff; transition: all .15s;
}
.profile-card:hover { border-color: #d6e4fb; box-shadow: 0 4px 14px rgba(0,0,0,.04); }
.profile-card.def { border-color: #bcdcff; background: #f7fbff; }
.profile-main { flex: 1; min-width: 220px; }
.profile-name { font-size: 15px; font-weight: 600; color: #1d1d1f; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.tag { font-size: 11px; border-radius: 7px; padding: 1px 7px; font-weight: 500; }
.def-tag { background: #007AFF; color: #fff; }
.nokey-tag { background: #fff3e0; color: #c77700; }
.profile-meta { margin-top: 4px; font-size: 12.5px; color: #8a8a8f; display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.profile-meta i { color: #AF52DE; }
.dot-sep { color: #d0d0d6; }
.profile-uses { margin-top: 7px; display: flex; gap: 6px; flex-wrap: wrap; }
.use-chip { font-size: 11px; background: #eef4ff; color: #2f6fd6; border-radius: 7px; padding: 2px 8px; }
.profile-acts { display: flex; gap: 6px; flex-wrap: wrap; }
.mini-btn {
  display: inline-flex; align-items: center; gap: 5px; height: 32px; padding: 0 12px;
  border: 1px solid #e2e2e8; background: #fff; color: #4a4a4f; border-radius: 9px; font-size: 12.5px; cursor: pointer; transition: all .15s;
}
.mini-btn:hover { border-color: #007AFF; color: #007AFF; }
.mini-btn.danger:hover { border-color: #ff3b30; color: #ff3b30; }
.mini-btn:disabled { opacity: .5; cursor: not-allowed; }
.profile-card .test-result { flex-basis: 100%; margin-top: 2px; }
.add-profile {
  display: inline-flex; align-items: center; gap: 8px; align-self: flex-start;
  height: 40px; padding: 0 18px; border: 1.5px dashed #c9d8ec; background: #f7fafe;
  color: #007AFF; border-radius: 12px; font-size: 13.5px; cursor: pointer; transition: all .15s;
}
.add-profile:hover { background: #eef4ff; border-color: #007AFF; }

/* ===== 档案编辑器 ===== */
.profile-editor { background: #f8fafc; border: 1px dashed #cfdcef; border-radius: 14px; padding: 16px; margin-bottom: 18px; }
.editor-title { font-size: 14px; font-weight: 600; color: #1d1d1f; margin-bottom: 12px; }

/* ===== 功能分配 ===== */
.routing { border-top: 1px solid #f0f0f4; padding-top: 16px; margin-top: 4px; }
.routing-title { font-size: 14px; font-weight: 600; color: #1d1d1f; margin: 0 0 12px; display: flex; align-items: center; gap: 7px; }
.routing-title i { color: #34C759; }
.route-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px 18px; }
.route-row { display: flex; align-items: center; gap: 10px; }
.route-row > label { font-size: 13px; color: #4a4a4f; min-width: 64px; }
.route-row select {
  flex: 1; height: 36px; border: 1px solid #e2e2e8; border-radius: 9px; padding: 0 10px;
  font-size: 13px; background: #fff; outline: none; cursor: pointer;
}
.route-row select:focus { border-color: #007AFF; }
.switch-row { grid-column: 1 / -1; flex-wrap: wrap; }
.switch { position: relative; display: inline-block; width: 44px; height: 24px; }
.switch input { opacity: 0; width: 0; height: 0; }
.slider { position: absolute; inset: 0; background: #d6d6dc; border-radius: 24px; transition: .2s; cursor: pointer; }
.slider::before { content: ''; position: absolute; height: 18px; width: 18px; left: 3px; top: 3px; background: #fff; border-radius: 50%; transition: .2s; }
.switch input:checked + .slider { background: #34C759; }
.switch input:checked + .slider::before { transform: translateX(20px); }
</style>
