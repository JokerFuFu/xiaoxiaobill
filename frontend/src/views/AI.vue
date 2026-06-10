<template>
  <div class="ai-page">
    <!-- 头部 -->
    <div class="ai-header">
      <div class="ai-title">
        <div class="ai-logo-badge">
          <img src="/images/logo_128.png" alt="小遥" />
        </div>
        <div>
          <h2>AI 助手</h2>
          <p class="ai-sub">
            <span class="status-dot" :class="{ on: enabled }"></span>
            {{ enabled ? `已连接 · ${model}` : '未配置模型' }}
          </p>
        </div>
      </div>
      <div class="ai-actions">
        <button class="ghost-btn" :class="{ on: showHistory }" @click="toggleHistory" title="历史对话">
          <i class="fas fa-clock-rotate-left"></i> 历史
        </button>
        <button class="ghost-btn" @click="newChat" title="开启新对话">
          <i class="fas fa-plus"></i> 新对话
        </button>
        <button v-if="messages.length" class="ghost-btn" @click="copyChat" title="复制整段对话">
          <i class="fas fa-copy"></i> 复制
        </button>
        <button v-if="messages.length" class="ghost-btn" @click="exportChat" title="导出为 Markdown 文件">
          <i class="fas fa-file-arrow-down"></i> 导出
        </button>
        <router-link to="/settings" class="ghost-btn" title="模型配置">
          <i class="fas fa-sliders-h"></i> 模型配置
        </router-link>
      </div>
    </div>

    <!-- 未配置 -->
    <div v-if="!enabled" class="ai-empty card">
      <img src="/images/logo_128.png" class="empty-logo" alt="" />
      <h3>还没有配置 AI 模型</h3>
      <p>到「设置 → AI 模型配置」填入服务地址和 API Key 即可开始对话。</p>
      <router-link to="/settings" class="primary-btn">去配置</router-link>
    </div>

    <!-- 主体:历史侧栏 + 对话 -->
    <div v-else class="ai-body">
      <!-- 历史侧栏 -->
      <transition name="slide">
        <div v-if="showHistory" class="history-panel card">
          <div class="history-head">
            <span>历史对话</span>
            <button class="hclose" @click="showHistory = false"><i class="fas fa-times"></i></button>
          </div>
          <div class="history-list">
            <div v-if="!chats.length" class="history-empty">还没有历史对话</div>
            <div
              v-for="c in chats" :key="c.id"
              class="history-item" :class="{ active: c.id === chatId }"
              @click="loadChat(c.id)"
            >
              <div class="hi-main">
                <span class="hi-title">{{ c.title }}</span>
                <span class="hi-meta">{{ shortTime(c.updated_at) }} · {{ c.count }} 条</span>
              </div>
              <button class="hi-del" @click.stop="renameChat(c)" title="重命名"><i class="fas fa-pen"></i></button>
              <button class="hi-del" @click.stop="removeChat(c)" title="删除"><i class="fas fa-trash-can"></i></button>
            </div>
          </div>
        </div>
      </transition>

      <!-- 对话区 -->
      <div class="chat card">
        <div class="messages" ref="msgBox">
          <!-- 欢迎态 -->
          <div v-if="messages.length === 0" class="welcome">
            <img src="/images/logo_128.png" class="welcome-logo" alt="" />
            <h3>你好，我是小遥</h3>
            <p>你的私人账单分析师，支持表格和图表回答</p>
            <div class="suggest-grid">
              <button v-for="ex in examples" :key="ex.q" class="suggest-card" @click="quickAsk(ex.q)">
                <i :class="ex.icon"></i>
                <span>{{ ex.q }}</span>
              </button>
            </div>
          </div>

          <!-- 消息流 -->
          <div v-for="(m, i) in messages" :key="i" :class="['msg-row', m.role]">
            <div class="avatar" :class="m.role">
              <img v-if="m.role === 'assistant'" src="/images/logo_128.png" alt="AI" />
              <i v-else class="fas fa-user"></i>
            </div>
            <div class="msg-body">
              <div class="bubble" :class="[m.role, { error: m.error, 'info-bubble': m.info }]">
                <template v-if="m.role === 'assistant'">
                  <template v-for="(seg, si) in segments(m.content)" :key="si">
                    <div v-if="seg.md" class="md" v-html="render(seg.text)"></div>
                    <AiChart v-else :spec="seg.spec" />
                  </template>
                </template>
                <span v-else>{{ m.content }}</span>
              </div>
              <div v-if="m.tools && m.tools.length" class="tools">
                <span v-for="(t, ti) in m.tools" :key="ti" class="tool-chip">
                  <i :class="t.name === 'export_transactions' ? 'fas fa-file-export' : 'fas fa-magnifying-glass-chart'"></i>
                  {{ toolLabel(t) }}
                </span>
              </div>
              <!-- 消息操作:复制 / 重新生成(末条) -->
              <div v-if="m.role === 'assistant' && !m.info" class="msg-actions">
                <button class="act-btn" @click="copyMsg(m)" title="复制回答"><i class="fas fa-copy"></i></button>
                <button v-if="i === messages.length - 1 && !loading" class="act-btn" @click="regenerate" title="重新生成">
                  <i class="fas fa-rotate-right"></i>
                </button>
              </div>
            </div>
          </div>

          <!-- 打字中 -->
          <div v-if="loading" class="msg-row assistant">
            <div class="avatar assistant"><img src="/images/logo_128.png" alt="AI" /></div>
            <div class="msg-body">
              <div class="bubble assistant typing">
                <span class="dot"></span><span class="dot"></span><span class="dot"></span>
              </div>
            </div>
          </div>
        </div>

        <!-- 输入区 -->
        <div class="composer">
          <textarea
            ref="inputBox"
            v-model="input"
            rows="1"
            @keydown.enter.exact.prevent="send"
            @input="autoGrow"
            :disabled="loading"
            placeholder="问问你的账单…(Enter 发送,Shift+Enter 换行)"
          ></textarea>
          <button v-if="loading" class="send-btn stop" @click="stopGen" title="停止生成">
            <i class="fas fa-stop"></i>
          </button>
          <button v-else class="send-btn" @click="send" :disabled="!input.trim()" title="发送">
            <i class="fas fa-paper-plane"></i>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import api from '@/api/client'
import AiChart from '@/components/AiChart.vue'
import { useUiStore } from '@/stores/ui'

const ui = useUiStore()

// 链接在新窗口打开(下载链接/外链),只加属性不放行脚本
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName === 'A') {
    node.setAttribute('target', '_blank')
    node.setAttribute('rel', 'noopener')
  }
})

const enabled = ref(true)
const model = ref('')
const messages = ref([])
const input = ref('')
const loading = ref(false)
const msgBox = ref(null)

// 会话历史
const chatId = ref(null)
const chats = ref([])
const showHistory = ref(false)

const examples = [
  { q: '我这个月花最多的是什么？', icon: 'fas fa-ranking-star' },
  { q: '最近半年每月支出趋势，画个折线图', icon: 'fas fa-chart-line' },
  { q: '这个月各分类支出占比，来个饼图', icon: 'fas fa-chart-pie' },
  { q: '超过 1000 元的大额支出有哪些？', icon: 'fas fa-coins' }
]

marked.setOptions({ breaks: true, gfm: true })

onMounted(async () => {
  try {
    const s = await api.aiStatus()
    enabled.value = s.enabled
    model.value = s.model || ''
  } catch (e) { enabled.value = false }
  if (enabled.value) refreshChats()
})

// ===== Markdown / 图表分段渲染 =====
function render(text) {
  const html = marked.parse(text || '')
  return DOMPurify.sanitize(html, { FORBID_TAGS: ['style', 'script', 'iframe'], FORBID_ATTR: ['onerror', 'onclick'] })
}

// 把 assistant 内容按 ```chart 代码块切成 [md|chart] 段
function segments(content) {
  const out = []
  const re = /```chart\s*\n?([\s\S]*?)```/g
  let last = 0
  let mt
  while ((mt = re.exec(content || '')) !== null) {
    if (mt.index > last) out.push({ md: true, text: content.slice(last, mt.index) })
    try {
      const spec = JSON.parse(mt[1])
      if (spec && spec.type) out.push({ md: false, spec })
      else out.push({ md: true, text: mt[0] })
    } catch (e) {
      out.push({ md: true, text: '```\n' + mt[1] + '\n```' })   // 非法 JSON 当代码块展示
    }
    last = re.lastIndex
  }
  if (last < (content || '').length) out.push({ md: true, text: content.slice(last) })
  return out.length ? out : [{ md: true, text: content || '' }]
}

function toolLabel(t) {
  const names = { data_overview: '数据概览', export_transactions: '导出文件', query_transactions: '查询交易' }
  const parts = [names[t.name] || t.name]
  if (t.count != null) parts.push(`${t.count} 笔`)
  if (t.total != null) parts.push(`¥${Number(t.total).toLocaleString('zh-CN', { maximumFractionDigits: 2 })}`)
  return parts.join(' · ')
}

function shortTime(s) {
  if (!s) return ''
  const today = new Date().toISOString().slice(0, 10).replace(/-/g, '-')
  return s.startsWith(today.slice(0, 10)) ? s.slice(11, 16) : s.slice(5, 10)
}

async function scrollDown() {
  await nextTick()
  if (msgBox.value) msgBox.value.scrollTop = msgBox.value.scrollHeight
}

// ===== 会话管理 =====
async function refreshChats() {
  try {
    const r = await api.aiChats()
    chats.value = r.chats || []
  } catch (e) { /* ignore */ }
}

function toggleHistory() {
  showHistory.value = !showHistory.value
  if (showHistory.value) refreshChats()
}

function newChat() {
  chatId.value = null
  messages.value = []
  showHistory.value = false
}

async function loadChat(id) {
  try {
    const r = await api.aiChatGet(id)
    chatId.value = id
    messages.value = (r.chat.messages || []).map(m => ({ role: m.role, content: m.content, tools: m.tools }))
    showHistory.value = false
    scrollDown()
  } catch (e) { /* ignore */ }
}

async function removeChat(c) {
  if (!confirm(`删除对话「${c.title}」？`)) return
  try {
    await api.aiChatDelete(c.id)
    if (c.id === chatId.value) newChat()
    await refreshChats()
  } catch (e) { /* ignore */ }
}

// ===== 发送 / 停止 / 重新生成 =====
const inputBox = ref(null)
let abortCtrl = null

function autoGrow() {
  const el = inputBox.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 140) + 'px'
}

function quickAsk(q) { input.value = q; send() }

function stopGen() {
  if (abortCtrl) abortCtrl.abort()
}

async function ask(q, { pushUser = true } = {}) {
  if (!q || loading.value) return
  if (pushUser) messages.value.push({ role: 'user', content: q })
  loading.value = true
  abortCtrl = new AbortController()
  scrollDown()
  try {
    const history = chatId.value ? undefined : messages.value
      .filter(m => !m.error && !m.info).slice(-7, -1)
      .map(m => ({ role: m.role, content: m.content }))
    const r = await api.aiChat(q, history, chatId.value, abortCtrl.signal)
    if (r.chat_id) chatId.value = r.chat_id
    messages.value.push({ role: 'assistant', content: r.answer, tools: r.tool_calls })
    refreshChats()
  } catch (e) {
    if (e.name === 'AbortError') {
      messages.value.push({ role: 'assistant', content: '⏹ 已停止生成。完整回答仍会保存到历史,稍后可在「历史」里查看。', info: true })
      setTimeout(refreshChats, 8000)   // 服务端跑完后刷新列表
    } else {
      messages.value.push({ role: 'assistant', content: '出错了：' + (e.message || '调用失败'), error: true })
    }
  } finally {
    loading.value = false
    abortCtrl = null
    scrollDown()
  }
}

async function send() {
  const q = input.value.trim()
  if (!q) return
  input.value = ''
  await nextTick(); autoGrow()
  ask(q)
}

function regenerate() {
  // 找最后一个用户提问,移除其后的 assistant 回答,重新生成
  const lastUserIdx = [...messages.value].map(m => m.role).lastIndexOf('user')
  if (lastUserIdx < 0) return
  const q = messages.value[lastUserIdx].content
  messages.value = messages.value.slice(0, lastUserIdx + 1)
  ask(q, { pushUser: false })
}

// ===== 复制 / 导出 =====
async function copyText(text, tip) {
  try {
    await navigator.clipboard.writeText(text)
    ui.showSuccess(tip || '已复制')
  } catch (e) {
    // 非 https/旧浏览器回退
    const ta = document.createElement('textarea')
    ta.value = text; document.body.appendChild(ta); ta.select()
    document.execCommand('copy'); document.body.removeChild(ta)
    ui.showSuccess(tip || '已复制')
  }
}

function copyMsg(m) { copyText(m.content, '回答已复制') }

function chatToMarkdown() {
  const title = (chats.value.find(c => c.id === chatId.value)?.title) || '对话'
  const lines = [`# ${title}`, '', `> 导出自 小遥账单 AI 助手 · ${new Date().toLocaleString('zh-CN')}`, '']
  for (const m of messages.value) {
    if (m.info) continue
    lines.push(m.role === 'user' ? '## 🙋 我' : '## 🤖 小遥', '', m.content, '')
  }
  return lines.join('\n')
}

function copyChat() { copyText(chatToMarkdown(), '整段对话已复制') }

function exportChat() {
  const title = (chats.value.find(c => c.id === chatId.value)?.title) || '对话'
  const blob = new Blob([chatToMarkdown()], { type: 'text/markdown;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `小遥对话-${title.slice(0, 16)}.md`
  a.click()
  URL.revokeObjectURL(a.href)
}

async function renameChat(c) {
  const t = prompt('重命名对话:', c.title)
  if (!t || t.trim() === c.title) return
  try {
    await api.aiChatRename(c.id, t.trim())
    await refreshChats()
  } catch (e) { ui.showError('重命名失败: ' + e.message) }
}
</script>

<style scoped>
.ai-page {
  padding: 24px;
  max-width: 1080px;
  margin: 0 auto;
  height: 100vh;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

/* ===== 头部 ===== */
.ai-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; gap: 12px; flex-wrap: wrap; }
.ai-title { display: flex; align-items: center; gap: 12px; }
.ai-logo-badge {
  width: 46px; height: 46px; border-radius: 14px;
  background: linear-gradient(135deg, #e8f1ff 0%, #f3e8ff 100%);
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 2px 8px rgba(0, 122, 255, 0.12);
}
.ai-logo-badge img { width: 38px; height: 38px; object-fit: contain; }
.ai-title h2 { margin: 0; font-size: 20px; color: #1d1d1f; letter-spacing: -0.02em; }
.ai-sub { margin: 2px 0 0; font-size: 12px; color: #86868b; display: flex; align-items: center; gap: 6px; }
.status-dot { width: 7px; height: 7px; border-radius: 50%; background: #d2d2d7; display: inline-block; }
.status-dot.on { background: #34C759; box-shadow: 0 0 0 3px rgba(52, 199, 89, 0.18); }
.ai-actions { display: flex; gap: 8px; }
.ghost-btn {
  display: inline-flex; align-items: center; gap: 6px;
  border: 1px solid #e5e5ea; background: #fff; color: #6e6e73;
  padding: 7px 14px; border-radius: 18px; font-size: 13px; cursor: pointer; text-decoration: none;
  transition: all .15s;
}
.ghost-btn:hover, .ghost-btn.on { border-color: #007AFF; color: #007AFF; }

/* ===== 卡片 ===== */
.card { background: #fff; border: 1px solid #ebebf0; border-radius: 18px; box-shadow: 0 2px 12px rgba(0,0,0,.04); }

/* ===== 未配置 ===== */
.ai-empty { text-align: center; padding: 60px 24px; }
.empty-logo { width: 72px; height: 72px; opacity: .9; }
.ai-empty h3 { margin: 14px 0 6px; color: #1d1d1f; }
.ai-empty p { color: #86868b; font-size: 14px; margin: 0 0 20px; }
.primary-btn {
  display: inline-block; background: #007AFF; color: #fff; text-decoration: none;
  padding: 10px 26px; border-radius: 12px; font-size: 14px;
}

/* ===== 主体布局 ===== */
.ai-body { flex: 1; display: flex; gap: 14px; min-height: 0; }

/* 历史侧栏 */
.history-panel { width: 240px; flex-shrink: 0; display: flex; flex-direction: column; overflow: hidden; }
.history-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 16px; border-bottom: 1px solid #f0f0f3;
  font-size: 14px; font-weight: 500; color: #1d1d1f;
}
.hclose { border: none; background: none; color: #b3b8bf; cursor: pointer; }
.hclose:hover { color: #6e6e73; }
.history-list { flex: 1; overflow-y: auto; padding: 8px; }
.history-empty { color: #b3b8bf; font-size: 12.5px; text-align: center; padding: 30px 0; }
.history-item {
  display: flex; align-items: center; gap: 6px;
  padding: 9px 11px; border-radius: 10px; cursor: pointer; transition: background .12s;
}
.history-item:hover { background: #f5f7fa; }
.history-item.active { background: #eaf3ff; }
.hi-main { flex: 1; min-width: 0; }
.hi-title { display: block; font-size: 13px; color: #1d1d1f; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.history-item.active .hi-title { color: #007AFF; font-weight: 500; }
.hi-meta { font-size: 11px; color: #9aa0a6; }
.hi-del { border: none; background: none; color: transparent; cursor: pointer; font-size: 12px; padding: 4px; }
.history-item:hover .hi-del { color: #c9ced6; }
.hi-del:hover { color: #ff3b30 !important; }

.slide-enter-active, .slide-leave-active { transition: all .18s ease; }
.slide-enter-from, .slide-leave-to { opacity: 0; transform: translateX(-12px); width: 0; }

/* ===== 对话 ===== */
.chat { flex: 1; display: flex; flex-direction: column; min-height: 0; min-width: 0; overflow: hidden; }
.messages { flex: 1; overflow-y: auto; padding: 24px; }

/* 欢迎态 */
.welcome { text-align: center; padding: 40px 12px 20px; }
.welcome-logo { width: 84px; height: 84px; }
.welcome h3 { margin: 12px 0 4px; font-size: 20px; color: #1d1d1f; }
.welcome p { color: #86868b; font-size: 13px; margin: 0 0 24px; }
.suggest-grid {
  display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px; max-width: 560px; margin: 0 auto;
}
.suggest-card {
  display: flex; align-items: center; gap: 10px; text-align: left;
  background: #f7f8fa; border: 1px solid transparent; border-radius: 14px;
  padding: 14px 16px; font-size: 13px; color: #3a3a3c; cursor: pointer;
  transition: all .15s;
}
.suggest-card:hover { background: #eef5ff; border-color: #b9d8ff; color: #007AFF; transform: translateY(-1px); }
.suggest-card i { color: #007AFF; font-size: 15px; width: 18px; }

/* 消息行 */
.msg-row { display: flex; gap: 10px; margin-bottom: 20px; }
.msg-row.user { flex-direction: row-reverse; }
.avatar {
  width: 34px; height: 34px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center; overflow: hidden;
  margin-top: 2px;
}
.avatar.assistant { background: linear-gradient(135deg, #eaf3ff, #f3ebff); border: 1px solid #e8eef8; }
.avatar.assistant img { width: 26px; height: 26px; object-fit: contain; }
.avatar.user { background: linear-gradient(135deg, #007AFF, #4DA3FF); color: #fff; font-size: 13px; }
.msg-body { max-width: 82%; min-width: 0; display: flex; flex-direction: column; }
.msg-row.user .msg-body { align-items: flex-end; }
.msg-row.assistant .msg-body { flex: 1; }

.bubble { padding: 11px 15px; border-radius: 16px; font-size: 14px; line-height: 1.7; word-break: break-word; }
.bubble.user {
  background: linear-gradient(135deg, #007AFF, #2E8FFF);
  color: #fff; border-top-right-radius: 6px;
  box-shadow: 0 2px 8px rgba(0, 122, 255, 0.22);
}
.bubble.assistant { background: #f6f7f9; color: #1d1d1f; border-top-left-radius: 6px; }
.bubble.error { background: #fff2f1; color: #c0392b; border: 1px solid #ffd9d5; }

/* 打字中 */
.typing { display: inline-flex; gap: 5px; padding: 14px 16px; }
.typing .dot { width: 7px; height: 7px; background: #b9c0c9; border-radius: 50%; animation: blink 1.2s infinite ease-in-out; }
.typing .dot:nth-child(2) { animation-delay: .18s; }
.typing .dot:nth-child(3) { animation-delay: .36s; }
@keyframes blink { 0%, 70%, 100% { opacity: .3; transform: translateY(0); } 35% { opacity: 1; transform: translateY(-3px); } }

/* 工具痕迹 */
.tools { margin-top: 7px; display: flex; flex-wrap: wrap; gap: 6px; }
.tool-chip {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 11px; color: #6e6e73; background: #fff;
  border: 1px solid #ebebf0; border-radius: 12px; padding: 3px 10px;
}
.tool-chip i { color: #AF52DE; font-size: 10px; }

/* ===== Markdown 渲染 ===== */
.md :deep(p) { margin: 0 0 8px; }
.md :deep(p:last-child) { margin-bottom: 0; }
.md :deep(strong) { color: #0a59c9; font-weight: 600; }
.md :deep(ul), .md :deep(ol) { margin: 4px 0 8px; padding-left: 20px; }
.md :deep(li) { margin: 3px 0; }
.md :deep(code) { background: #eef0f3; border-radius: 5px; padding: 1px 6px; font-size: 12.5px; }
.md :deep(h1), .md :deep(h2), .md :deep(h3), .md :deep(h4) { margin: 10px 0 6px; font-size: 15px; }
.md :deep(table) {
  width: 100%; border-collapse: separate; border-spacing: 0;
  margin: 10px 0; font-size: 13px; background: #fff;
  border: 1px solid #e8e8ed; border-radius: 10px; overflow: hidden;
}
.md :deep(th) {
  background: #f0f4fa; color: #3a3a3c; font-weight: 600;
  padding: 8px 12px; text-align: left; border-bottom: 1px solid #e8e8ed;
}
.md :deep(td) { padding: 7px 12px; border-bottom: 1px solid #f2f2f5; font-variant-numeric: tabular-nums; }
.md :deep(tr:last-child td) { border-bottom: none; }
.md :deep(tr:nth-child(even) td) { background: #fafbfc; }
.md :deep(blockquote) { margin: 6px 0; padding: 6px 12px; border-left: 3px solid #cfe1ff; color: #6e6e73; background: #f8faff; border-radius: 0 8px 8px 0; }
.md :deep(hr) { border: none; border-top: 1px solid #ebebf0; margin: 10px 0; }

/* ===== 输入区 ===== */
.composer {
  display: flex; gap: 10px; padding: 14px 16px;
  border-top: 1px solid #f0f0f3; background: #fcfcfd;
}
.composer textarea {
  flex: 1; min-height: 46px; max-height: 140px; border: 1px solid #e2e2e8; border-radius: 23px;
  padding: 12px 20px; font-size: 14px; line-height: 1.5; outline: none; background: #fff;
  resize: none; font-family: inherit; transition: border-color .15s, box-shadow .15s;
  box-sizing: border-box;
}
.composer textarea:focus { border-color: #007AFF; box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.10); }
.send-btn {
  width: 46px; height: 46px; border: none; border-radius: 50%;
  background: linear-gradient(135deg, #007AFF, #2E8FFF); color: #fff;
  font-size: 16px; cursor: pointer; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 3px 10px rgba(0, 122, 255, 0.3);
  transition: all .15s;
}
.send-btn:hover:not(:disabled) { transform: scale(1.05); }
.send-btn:disabled { opacity: .45; cursor: not-allowed; box-shadow: none; }
.send-btn.stop {
  background: linear-gradient(135deg, #ff5b51, #ff3b30);
  box-shadow: 0 3px 10px rgba(255, 59, 48, 0.3);
  animation: pulse 1.6s infinite;
}
@keyframes pulse { 0%,100% { box-shadow: 0 3px 10px rgba(255,59,48,.3); } 50% { box-shadow: 0 3px 16px rgba(255,59,48,.55); } }

/* 消息操作条 */
.msg-actions { margin-top: 6px; display: flex; gap: 4px; opacity: 0; transition: opacity .15s; }
.msg-row:hover .msg-actions { opacity: 1; }
.act-btn {
  border: none; background: none; color: #b3b8bf; cursor: pointer;
  font-size: 12px; padding: 4px 7px; border-radius: 7px; transition: all .12s;
}
.act-btn:hover { color: #007AFF; background: #eef5ff; }

/* 信息提示气泡(停止生成等) */
.bubble.info-bubble { background: #f6f7f9; color: #9aa0a6; font-size: 13px; }

/* Markdown 链接(含下载链接) */
.md :deep(a) {
  color: #007AFF; text-decoration: none; font-weight: 500;
  border-bottom: 1px dashed #9cc5ff;
}
.md :deep(a:hover) { border-bottom-style: solid; }

@media (max-width: 820px) {
  .history-panel { position: absolute; z-index: 20; height: 70%; }
}
</style>
