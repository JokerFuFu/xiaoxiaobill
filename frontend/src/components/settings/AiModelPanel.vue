<template>
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
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useUiStore } from '@/stores/ui'
import api from '@/api/client'

const uiStore = useUiStore()

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

onMounted(async () => {
  await loadAiConfig()
})
</script>

<style scoped>
.ai-section { margin: 26px 0; }
.ai-section .section-title { display: flex; align-items: center; gap: 8px; font-size: 17px; margin-bottom: 12px; }
.title-icon.ai-color { color: #AF52DE; }
.ai-card {
  background: var(--card-bg, #fff); border: 1px solid #ebebf0; border-radius: 16px;
  padding: 20px 22px; box-shadow: 0 2px 10px rgba(0,0,0,.03);
}
.ai-desc { color: #6e6e73; font-size: 13px; margin: 0 0 14px; line-height: 1.7; }
.muted { color: #9aa0a6; font-size: 12px; font-weight: normal; }

.provider-row { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
.provider-chip {
  border: 1px solid #e2e2e8; background: #fff; color: #3a3a3c;
  padding: 6px 14px; border-radius: 16px; font-size: 13px; cursor: pointer; transition: all .15s;
}
.provider-chip:hover { border-color: #007AFF; color: #007AFF; }
.provider-chip.active { background: #eaf3ff; border-color: #007AFF; color: #007AFF; font-weight: 500; }

.cfg-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px 16px; }
.cfg-field { display: flex; flex-direction: column; }
.cfg-field.full { grid-column: 1 / -1; }
.cfg-field label { font-size: 12.5px; color: #6e6e73; margin-bottom: 6px; }
.cfg-field input {
  height: 40px; border: 1px solid #e2e2e8; border-radius: 10px; padding: 0 13px;
  font-size: 13.5px; outline: none; transition: all .15s; background: #fff;
}
.cfg-field input:focus { border-color: #007AFF; box-shadow: 0 0 0 3px rgba(0,122,255,.08); }
@media (max-width: 760px) { .cfg-grid { grid-template-columns: 1fr; } }

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
