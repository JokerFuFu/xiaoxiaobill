<template>
  <div class="ai-page">
    <div class="ai-header">
      <h2><i class="fas fa-robot"></i> AI 助手</h2>
      <div class="tabs">
        <button :class="{ active: tab === 'chat' }" @click="tab = 'chat'">对话检索</button>
        <button :class="{ active: tab === 'recognize' }" @click="tab = 'recognize'">智能识别账单</button>
      </div>
    </div>

    <div v-if="!enabled" class="ai-disabled">
      <i class="fas fa-plug"></i>
      <p>AI 功能未启用。请在后端配置 <code>ANTHROPIC_API_KEY</code> 后重启。</p>
    </div>

    <!-- 对话 -->
    <div v-else-if="tab === 'chat'" class="chat">
      <div class="messages" ref="msgBox">
        <div v-if="messages.length === 0" class="hint">
          <p>直接用大白话问我，例如：</p>
          <div class="examples">
            <span v-for="ex in examples" :key="ex" @click="quickAsk(ex)">{{ ex }}</span>
          </div>
        </div>
        <div v-for="(m, i) in messages" :key="i" :class="['msg', m.role]">
          <div class="bubble">
            <div v-if="m.role === 'assistant'" v-html="render(m.content)"></div>
            <span v-else>{{ m.content }}</span>
            <div v-if="m.tools && m.tools.length" class="tools">
              <span v-for="(t, ti) in m.tools" :key="ti" class="tool-chip">
                🔎 {{ t.name }}{{ t.count != null ? ` · ${t.count}笔` : '' }}{{ t.total != null ? ` · ¥${t.total}` : '' }}
              </span>
            </div>
          </div>
        </div>
        <div v-if="loading" class="msg assistant"><div class="bubble typing">思考中…</div></div>
      </div>
      <div class="composer">
        <input v-model="input" @keyup.enter="send" :disabled="loading" placeholder="问问你的账单…（回车发送）" />
        <button @click="send" :disabled="loading || !input.trim()">发送</button>
      </div>
    </div>

    <!-- 识别账单 -->
    <div v-else class="recognize">
      <p class="desc">把不支持格式的账单（任意 CSV/Excel/PDF 文本，或直接粘贴文字）交给 AI 提取成交易记录。</p>
      <div class="rec-input">
        <textarea v-model="recText" placeholder="粘贴账单文字内容…"></textarea>
        <div class="rec-actions">
          <input type="file" ref="recFile" accept=".csv,.txt,.xlsx,.pdf" @change="onRecFile" />
          <button @click="doRecognize" :disabled="recLoading">{{ recLoading ? '识别中…' : '开始识别' }}</button>
        </div>
      </div>
      <div v-if="recRows.length" class="rec-result">
        <div class="rec-head">
          <span>识别到 {{ recRows.length }} 笔</span>
          <select v-model="recMember">
            <option v-for="m in members" :key="m.id" :value="m.id">归属：{{ m.name }}</option>
          </select>
          <button class="import-btn" @click="doImport" :disabled="recLoading">导入到账单</button>
        </div>
        <table>
          <thead><tr><th>时间</th><th>分类</th><th>对方</th><th>说明</th><th>收支</th><th>金额</th></tr></thead>
          <tbody>
            <tr v-for="(r, i) in recRows" :key="i">
              <td>{{ r['交易时间'] }}</td><td>{{ r['交易分类'] }}</td><td>{{ r['交易对方'] }}</td>
              <td>{{ r['商品说明'] }}</td><td>{{ r['收/支'] }}</td><td class="amt">{{ r['金额'] }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import api from '@/api/client'
import { useUiStore } from '@/stores/ui'
import { useMembersStore } from '@/stores/members'

const ui = useUiStore()
const membersStore = useMembersStore()

const enabled = ref(true)
const tab = ref('chat')

// 对话
const messages = ref([])
const input = ref('')
const loading = ref(false)
const msgBox = ref(null)
const examples = [
  '我这个月花最多的是什么？',
  '今年餐饮一共花了多少？',
  '帮我看看大额支出（超过1000）有哪些',
  '我每个月的收入和支出趋势'
]

// 识别
const recText = ref('')
const recFile = ref(null)
const recRows = ref([])
const recLoading = ref(false)
const recMember = ref('')
const members = ref([])

onMounted(async () => {
  try {
    const s = await api.aiStatus()
    enabled.value = s.enabled
  } catch (e) { enabled.value = false }
  await membersStore.load()
  members.value = membersStore.members
  recMember.value = membersStore.defaultId()
})

function render(text) {
  // 极简 markdown：**加粗** + 换行
  return (text || '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
}

async function scrollDown() {
  await nextTick()
  if (msgBox.value) msgBox.value.scrollTop = msgBox.value.scrollHeight
}

function quickAsk(q) { input.value = q; send() }

async function send() {
  const q = input.value.trim()
  if (!q || loading.value) return
  messages.value.push({ role: 'user', content: q })
  input.value = ''
  loading.value = true
  scrollDown()
  try {
    const history = messages.value.slice(-7, -1).map(m => ({ role: m.role, content: m.content }))
    const r = await api.aiChat(q, history)
    messages.value.push({ role: 'assistant', content: r.answer, tools: r.tool_calls })
  } catch (e) {
    messages.value.push({ role: 'assistant', content: '出错了：' + (e.message || '调用失败') })
  } finally {
    loading.value = false
    scrollDown()
  }
}

function onRecFile() { /* 文件选择后由 doRecognize 处理 */ }

async function doRecognize() {
  recLoading.value = true
  recRows.value = []
  try {
    let r
    const f = recFile.value && recFile.value.files[0]
    if (f) {
      const fd = new FormData()
      fd.append('file', f)
      r = await api.aiRecognize(fd)
    } else if (recText.value.trim()) {
      r = await api.aiRecognizeText(recText.value, '')
    } else {
      ui.showError('请粘贴文字或选择文件')
      return
    }
    recRows.value = r.rows || []
    if (!recRows.value.length) ui.showError('没识别出交易记录')
  } catch (e) {
    ui.showError('识别失败：' + (e.message || ''))
  } finally {
    recLoading.value = false
  }
}

async function doImport() {
  recLoading.value = true
  try {
    const r = await api.aiRecognizeImport(recRows.value, recMember.value, 'AI识别账单')
    ui.showSuccess(`已导入 ${r.count} 笔到账单`)
    recRows.value = []
    recText.value = ''
    if (recFile.value) recFile.value.value = ''
  } catch (e) {
    ui.showError('导入失败：' + (e.message || ''))
  } finally {
    recLoading.value = false
  }
}
</script>

<style scoped>
.ai-page { padding: 24px; max-width: 900px; margin: 0 auto; height: calc(100vh - var(--header-height, 0px)); display: flex; flex-direction: column; }
.ai-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; flex-wrap: wrap; gap: 12px; }
.ai-header h2 { margin: 0; font-size: 22px; color: #1d1d1f; }
.ai-header h2 i { color: #AF52DE; margin-right: 8px; }
.tabs button { border: 1px solid #d2d2d7; background: #fff; padding: 7px 16px; border-radius: 18px; margin-left: 8px; cursor: pointer; font-size: 14px; }
.tabs button.active { background: #007AFF; color: #fff; border-color: #007AFF; }
.ai-disabled { text-align: center; color: #86868b; margin-top: 80px; }
.ai-disabled i { font-size: 40px; }

.chat { flex: 1; display: flex; flex-direction: column; min-height: 0; background: #fff; border-radius: 14px; border: 1px solid #eee; overflow: hidden; }
.messages { flex: 1; overflow-y: auto; padding: 18px; }
.hint { color: #86868b; }
.examples { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.examples span { background: #f0f2f5; border-radius: 16px; padding: 6px 14px; cursor: pointer; font-size: 13px; }
.examples span:hover { background: #e2e8f0; }
.msg { display: flex; margin-bottom: 14px; }
.msg.user { justify-content: flex-end; }
.bubble { max-width: 80%; padding: 10px 14px; border-radius: 14px; font-size: 14px; line-height: 1.6; }
.msg.user .bubble { background: #007AFF; color: #fff; border-bottom-right-radius: 4px; }
.msg.assistant .bubble { background: #f0f2f5; color: #1d1d1f; border-bottom-left-radius: 4px; }
.typing { color: #86868b; }
.tools { margin-top: 8px; display: flex; flex-wrap: wrap; gap: 6px; }
.tool-chip { font-size: 11px; color: #6e6e73; background: rgba(0,0,0,.05); border-radius: 10px; padding: 2px 8px; }
.composer { display: flex; gap: 10px; padding: 12px; border-top: 1px solid #eee; }
.composer input { flex: 1; height: 42px; border: 1px solid #d2d2d7; border-radius: 21px; padding: 0 18px; font-size: 14px; outline: none; }
.composer input:focus { border-color: #007AFF; }
.composer button { height: 42px; padding: 0 22px; border: none; border-radius: 21px; background: #007AFF; color: #fff; cursor: pointer; }
.composer button:disabled { opacity: .5; cursor: not-allowed; }

.recognize { background: #fff; border-radius: 14px; border: 1px solid #eee; padding: 20px; overflow-y: auto; }
.recognize .desc { color: #6e6e73; font-size: 13px; }
.rec-input textarea { width: 100%; min-height: 140px; border: 1px solid #d2d2d7; border-radius: 10px; padding: 12px; font-size: 13px; resize: vertical; }
.rec-actions { display: flex; align-items: center; gap: 14px; margin-top: 10px; }
.rec-actions button { padding: 8px 18px; border: none; border-radius: 10px; background: #007AFF; color: #fff; cursor: pointer; }
.rec-result { margin-top: 20px; }
.rec-head { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.rec-head select { height: 34px; border-radius: 8px; border: 1px solid #d2d2d7; padding: 0 10px; }
.import-btn { padding: 7px 16px; border: none; border-radius: 8px; background: #34C759; color: #fff; cursor: pointer; }
.rec-result table { width: 100%; border-collapse: collapse; font-size: 13px; }
.rec-result th, .rec-result td { border-bottom: 1px solid #f0f0f0; padding: 7px 8px; text-align: left; }
.rec-result .amt { text-align: right; font-variant-numeric: tabular-nums; }
</style>
