<template>
  <div class="mini-chat">
    <div ref="msgBox" class="mc-messages">
      <!-- 空态:欢迎 + 示例 -->
      <div v-if="!messages.length" class="mc-empty">
        <div class="mc-hello">
          <span class="mc-logo"><img src="/images/logo_128.png" alt="" /></span>
          <div>
            <div class="mc-hello-title">问问你的账单</div>
            <div class="mc-hello-sub">{{ enabled ? '用大白话问消费、收入、趋势,我直接查你的真实数据回答' : 'AI 未配置,去「设置 → AI 与模型」填个模型即可启用' }}</div>
          </div>
        </div>
        <div v-if="enabled" class="mc-examples">
          <button v-for="e in examples" :key="e.q" class="mc-example" @click="send(e.q)">
            <i :class="e.icon"></i> {{ e.q }}
          </button>
        </div>
      </div>

      <!-- 消息 -->
      <div v-for="(m, i) in messages" :key="i" class="mc-msg" :class="m.role">
        <span v-if="m.role === 'assistant'" class="mc-avatar"><img src="/images/logo_128.png" alt="" /></span>
        <div class="mc-bubble" :class="{ err: m.error, info: m.info }">
          <template v-if="m.role === 'assistant' && !m.error && !m.info">
            <template v-for="(seg, j) in segments(m.content)" :key="j">
              <div v-if="seg.md" class="mc-md" v-html="render(seg.text)"></div>
              <AiChart v-else :spec="seg.spec" />
            </template>
            <div v-if="m.tools && m.tools.length" class="mc-tools">
              <span v-for="(t, k) in m.tools" :key="k" class="mc-tool">{{ toolLabel(t) }}</span>
            </div>
          </template>
          <template v-else>{{ m.content }}</template>
        </div>
      </div>

      <!-- 打字中 -->
      <div v-if="loading" class="mc-msg assistant">
        <span class="mc-avatar"><img src="/images/logo_128.png" alt="" /></span>
        <div class="mc-bubble mc-typing"><span></span><span></span><span></span></div>
      </div>
    </div>

    <!-- 输入 -->
    <div class="mc-composer">
      <textarea
        v-model="input" ref="ta" class="mc-input" rows="1"
        :placeholder="enabled ? '问点什么…（Enter 发送，Shift+Enter 换行）' : 'AI 未配置'"
        :disabled="!enabled" @keydown.enter.exact.prevent="send()" @input="autoGrow"
      ></textarea>
      <button v-if="loading" class="mc-send stop" @click="stop" title="停止"><i class="fas fa-stop"></i></button>
      <button v-else class="mc-send" :disabled="!enabled || !input.trim()" @click="send()" title="发送"><i class="fas fa-paper-plane"></i></button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import api from '@/api/client'
import AiChart from '@/components/AiChart.vue'

const examples = [
  { q: '我这个月花最多的是什么？', icon: 'fas fa-ranking-star' },
  { q: '最近半年每月支出趋势，画个折线图', icon: 'fas fa-chart-line' },
  { q: '这个月各分类支出占比，来个饼图', icon: 'fas fa-chart-pie' },
  { q: '今年我真实花了多少、赚了多少？', icon: 'fas fa-scale-balanced' },
]

const enabled = ref(true)
const messages = ref([])
const input = ref('')
const loading = ref(false)
const chatId = ref(null)
const msgBox = ref(null)
const ta = ref(null)
let abortCtrl = null

marked.setOptions({ breaks: true, gfm: true })
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName === 'A') { node.setAttribute('target', '_blank'); node.setAttribute('rel', 'noopener') }
})

onMounted(async () => {
  try {
    const s = await api.aiStatus()
    enabled.value = !!s.enabled
  } catch (e) { enabled.value = false }
})

function render(text) {
  const html = marked.parse(text || '')
  return DOMPurify.sanitize(html, { FORBID_TAGS: ['style', 'script', 'iframe'], FORBID_ATTR: ['onerror', 'onclick'] })
}
function segments(content) {
  const out = []
  const re = /```chart\s*\n?([\s\S]*?)```/g
  let last = 0, mt
  while ((mt = re.exec(content || '')) !== null) {
    if (mt.index > last) out.push({ md: true, text: content.slice(last, mt.index) })
    try {
      const spec = JSON.parse(mt[1])
      if (spec && spec.type) out.push({ md: false, spec }); else out.push({ md: true, text: mt[0] })
    } catch (e) { out.push({ md: true, text: '```\n' + mt[1] + '\n```' }) }
    last = re.lastIndex
  }
  if (last < (content || '').length) out.push({ md: true, text: content.slice(last) })
  return out.length ? out : [{ md: true, text: content || '' }]
}
function toolLabel(t) {
  const names = { data_overview: '数据概览', export_transactions: '导出文件', query_transactions: '查询交易' }
  const p = [names[t.name] || t.name]
  if (t.count != null) p.push(`${t.count} 笔`)
  if (t.total != null) p.push(`¥${Number(t.total).toLocaleString('zh-CN', { maximumFractionDigits: 2 })}`)
  return p.join(' · ')
}
async function scrollDown() {
  await nextTick()
  if (msgBox.value) msgBox.value.scrollTop = msgBox.value.scrollHeight
}
function autoGrow() {
  const el = ta.value; if (!el) return
  el.style.height = 'auto'; el.style.height = Math.min(el.scrollHeight, 120) + 'px'
}
function stop() { if (abortCtrl) abortCtrl.abort() }

async function send(q) {
  const text = (q != null ? q : input.value).trim()
  if (!text || loading.value || !enabled.value) return
  if (q == null) { input.value = ''; nextTick(autoGrow) }
  messages.value.push({ role: 'user', content: text })
  loading.value = true
  abortCtrl = new AbortController()
  scrollDown()
  try {
    const history = chatId.value ? undefined : messages.value
      .filter(m => !m.error && !m.info).slice(-7, -1).map(m => ({ role: m.role, content: m.content }))
    const r = await api.aiChat(text, history, chatId.value, abortCtrl.signal)
    if (r.chat_id) chatId.value = r.chat_id
    messages.value.push({ role: 'assistant', content: r.answer, tools: r.tool_calls })
  } catch (e) {
    if (e.name === 'AbortError') {
      messages.value.push({ role: 'assistant', content: '⏹ 已停止。完整回答仍会保存到「AI 助手」的历史里。', info: true })
    } else {
      messages.value.push({ role: 'assistant', content: '出错了：' + (e.message || '调用失败'), error: true })
    }
  } finally {
    loading.value = false; abortCtrl = null; scrollDown()
  }
}

defineExpose({ send })
</script>

<style scoped>
.mini-chat { display: flex; flex-direction: column; height: 100%; min-height: 0; }
.mc-messages { flex: 1; overflow-y: auto; padding: 4px 2px 8px; min-height: 0; }

.mc-empty { padding: 8px 4px; }
.mc-hello { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
.mc-logo img, .mc-avatar img { width: 34px; height: 34px; border-radius: 50%; object-fit: contain; background: #f3eefd; }
.mc-hello-title { font-size: 16px; font-weight: 600; color: #1d1d1f; }
.mc-hello-sub { font-size: 13px; color: #8a8a8f; margin-top: 2px; line-height: 1.5; }
.mc-examples { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
@media (max-width: 600px) { .mc-examples { grid-template-columns: 1fr; } }
.mc-example {
  display: flex; align-items: center; gap: 8px; text-align: left;
  border: 1px solid #ececf2; background: #fbfbfd; color: #3a3a3c; border-radius: 11px;
  padding: 10px 12px; font-size: 13px; cursor: pointer; transition: all .15s;
}
.mc-example i { color: #AF52DE; }
.mc-example:hover { border-color: #AF52DE; background: #faf6ff; }

.mc-msg { display: flex; gap: 9px; margin: 12px 0; }
.mc-msg.user { flex-direction: row-reverse; }
.mc-avatar { flex-shrink: 0; }
.mc-bubble {
  max-width: 82%; padding: 10px 14px; border-radius: 14px; font-size: 14px; line-height: 1.7;
  background: #f5f6f8; color: #1d1d1f;
}
.mc-msg.user .mc-bubble { background: linear-gradient(135deg, #0a84ff, #0066e6); color: #fff; }
.mc-bubble.err { background: #fdeeec; color: #c0392b; }
.mc-bubble.info { background: #fff8e6; color: #9a7400; font-size: 13px; }
.mc-tools { margin-top: 8px; display: flex; flex-wrap: wrap; gap: 6px; }
.mc-tool { font-size: 11px; background: #eef4ff; color: #2f6fd6; border-radius: 7px; padding: 2px 8px; }

.mc-typing { display: inline-flex; gap: 4px; align-items: center; }
.mc-typing span { width: 6px; height: 6px; border-radius: 50%; background: #c0c0c8; animation: mcbounce 1.2s infinite; }
.mc-typing span:nth-child(2) { animation-delay: .2s; }
.mc-typing span:nth-child(3) { animation-delay: .4s; }
@keyframes mcbounce { 0%, 60%, 100% { transform: translateY(0); opacity: .5; } 30% { transform: translateY(-5px); opacity: 1; } }

/* markdown */
.mc-md :deep(p) { margin: 6px 0; }
.mc-md :deep(strong) { color: #0a59c9; }
.mc-md :deep(table) { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 13px; }
.mc-md :deep(th), .mc-md :deep(td) { border: 1px solid #ececf2; padding: 5px 9px; text-align: left; }
.mc-md :deep(th) { background: #f4f6fa; }
.mc-md :deep(tr:nth-child(even) td) { background: #fafbfd; }
.mc-md :deep(ul), .mc-md :deep(ol) { padding-left: 20px; margin: 6px 0; }
.mc-md :deep(a) { color: #007AFF; }
.mc-md :deep(code) { background: #eef0f4; border-radius: 4px; padding: 1px 5px; font-size: 12.5px; }

.mc-composer { display: flex; gap: 8px; align-items: flex-end; padding-top: 8px; border-top: 1px solid #f0f0f4; }
.mc-input {
  flex: 1; resize: none; border: 1px solid #e2e2e8; border-radius: 12px; padding: 10px 13px;
  font-size: 14px; line-height: 1.5; outline: none; font-family: inherit; max-height: 120px;
  transition: border-color .15s;
}
.mc-input:focus { border-color: #AF52DE; }
.mc-send {
  flex-shrink: 0; width: 40px; height: 40px; border: none; border-radius: 12px; cursor: pointer;
  background: linear-gradient(135deg, #AF52DE, #7B61FF); color: #fff; font-size: 15px; transition: opacity .15s;
}
.mc-send:hover { opacity: .9; }
.mc-send:disabled { opacity: .4; cursor: not-allowed; }
.mc-send.stop { background: #ff3b30; }
</style>
