<template>
  <div class="ai-analysis" :class="{ collapsed: !expanded }">
    <div class="aa-head" @click="expanded = !expanded">
      <div class="aa-title">
        <span class="aa-logo"><i class="fas fa-wand-magic-sparkles"></i></span>
        <span>AI 智能分析</span>
        <span class="aa-scope">{{ scopeLabel }}</span>
        <span v-if="report && report.cached" class="aa-flag cached">缓存</span>
      </div>
      <div class="aa-head-right" @click.stop>
        <!-- 周期选择 -->
        <select v-if="years.length" v-model.number="year" class="aa-sel" @change="onPeriodChange">
          <option v-for="y in years" :key="y" :value="y">{{ y }} 年</option>
        </select>
        <select v-if="scope === 'monthly'" v-model.number="month" class="aa-sel" @change="onPeriodChange">
          <option v-for="m in 12" :key="m" :value="m">{{ m }} 月</option>
        </select>
        <button class="aa-run" :disabled="loading" @click="run(true)">
          <i :class="loading ? 'fas fa-spinner fa-spin' : 'fas fa-bolt'"></i>
          {{ loading ? '分析中…' : (report ? '重新分析' : 'AI 分析') }}
        </button>
        <i class="fas fa-chevron-down aa-caret" :class="{ open: expanded }"></i>
      </div>
    </div>

    <transition name="aa-fade">
      <div v-show="expanded" class="aa-body">
        <div v-if="error" class="aa-empty err"><i class="fas fa-circle-exclamation"></i> {{ error }}</div>
        <div v-else-if="loading && !report" class="aa-empty"><i class="fas fa-spinner fa-spin"></i> 正在让模型解读本期数据…</div>
        <div v-else-if="report" class="aa-report">
          <div class="aa-md" v-html="rendered"></div>
          <div class="aa-foot">
            <span><i class="fas fa-robot"></i> {{ report.model || '模型' }}</span>
            <span><i class="fas fa-clock"></i> {{ report.generated_at }}</span>
            <span class="aa-period">{{ report.period_label }}</span>
          </div>
        </div>
        <div v-else-if="!enabled" class="aa-empty">
          <i class="fas fa-circle-info"></i>
          智能分析需要先配置模型。请到 <router-link to="/settings?tab=ai" class="aa-link">设置 → AI 与模型</router-link> 指定「智能分析」使用的模型。
        </div>
        <div v-else class="aa-empty">
          <i class="fas fa-lightbulb"></i>
          点「AI 分析」让模型基于本期账单数据生成洞察与建议。
          <span class="muted">（已开启每月自动分析时，每月首次打开会自动生成）</span>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import api from '@/api/client'
import { useUiStore } from '@/stores/ui'

const props = defineProps({ scope: { type: String, required: true } })
const uiStore = useUiStore()

marked.setOptions({ breaks: true, gfm: true })

const SCOPE_LABELS = { yearly: '年度总览', monthly: '月度分析', category: '分类分析', time: '时间分析', channel: '渠道分析', reconcile: '对账中心' }
const scopeLabel = computed(() => SCOPE_LABELS[props.scope] || props.scope)

const expanded = ref(true)
const years = ref([])
const year = ref(null)
const month = ref(new Date().getMonth() + 1)   // 默认当前月
const report = ref(null)
const loading = ref(false)
const error = ref('')
const auto = ref(true)
const enabled = ref(true)

const rendered = computed(() => {
  const html = marked.parse((report.value && report.value.summary) || '')
  return DOMPurify.sanitize(html, { FORBID_TAGS: ['style', 'script', 'iframe'], FORBID_ATTR: ['onerror', 'onclick'] })
})

const isLatest = computed(() => years.value.length && year.value === years.value[0])

async function loadYears() {
  if (years.value.length) return
  try {
    const r = await api.getAvailableYears()
    years.value = r.years || []
    if (years.value.length && !year.value) year.value = years.value[0]
  } catch (e) { /* 无数据时忽略 */ }
}

async function fetchCached(triggerAuto = false) {
  error.value = ''
  report.value = null
  if (!year.value) return
  try {
    const params = { scope: props.scope, year: year.value }
    if (props.scope === 'monthly') params.month = month.value
    const r = await api.aiAnalyzeGet(params)
    auto.value = r.auto !== false
    enabled.value = r.enabled !== false
    report.value = r.report || null
    // 自动触发:已配置模型 + 开启自动 + 当前是最新周期 + 还没有本期报告 → 生成一次
    if (triggerAuto && !report.value && enabled.value && auto.value && isLatest.value) {
      run(false)
    }
  } catch (e) { /* 取缓存失败不报错 */ }
}

async function run(force) {
  if (loading.value) return
  loading.value = true
  error.value = ''
  try {
    const payload = { scope: props.scope, year: year.value, force }
    if (props.scope === 'monthly') payload.month = month.value
    const r = await api.aiAnalyzeRun(payload)
    report.value = r.report
    expanded.value = true
  } catch (e) {
    error.value = e.message || '分析失败'
    if (force) uiStore.showError('分析失败: ' + error.value)
  } finally { loading.value = false }
}

function onPeriodChange() { fetchCached(false) }

watch(() => props.scope, async () => { await loadYears(); fetchCached(true) })

onMounted(async () => {
  await loadYears()
  fetchCached(true)
})
</script>

<style scoped>
.ai-analysis {
  border: 1px solid #ecdcff; border-radius: 16px; margin-bottom: 20px; overflow: hidden;
  background: linear-gradient(135deg, #faf6ff 0%, #f4f8ff 100%);
  box-shadow: 0 2px 12px rgba(175, 82, 222, .06);
}
.aa-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 12px 16px; cursor: pointer; flex-wrap: wrap; }
.aa-title { display: flex; align-items: center; gap: 9px; font-size: 15px; font-weight: 600; color: #2a2a2e; }
.aa-logo {
  width: 26px; height: 26px; border-radius: 8px; display: inline-flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #AF52DE, #5856D6); color: #fff; font-size: 13px;
}
.aa-scope { font-size: 12px; color: #8a6cc0; background: #f1e7fb; border-radius: 7px; padding: 2px 8px; font-weight: 500; }
.aa-flag { font-size: 11px; border-radius: 6px; padding: 1px 7px; }
.aa-flag.cached { background: #eef1f4; color: #8a8a8f; }
.aa-head-right { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.aa-sel { height: 32px; border: 1px solid #e2d6f5; border-radius: 8px; padding: 0 8px; font-size: 13px; background: #fff; cursor: pointer; outline: none; }
.aa-run {
  display: inline-flex; align-items: center; gap: 6px; height: 32px; padding: 0 14px; border: none; border-radius: 9px;
  background: linear-gradient(135deg, #AF52DE, #7B61FF); color: #fff; font-size: 13px; cursor: pointer; transition: opacity .15s;
}
.aa-run:hover { opacity: .9; }
.aa-run:disabled { opacity: .6; cursor: not-allowed; }
.aa-caret { color: #b0a0c8; transition: transform .2s; font-size: 13px; }
.aa-caret.open { transform: rotate(180deg); }

.aa-body { padding: 0 16px 14px; }
.aa-empty { padding: 14px 16px; background: #fff; border-radius: 12px; color: #6e6e73; font-size: 13.5px; line-height: 1.7; }
.aa-empty.err { color: #c0392b; background: #fdeeec; }
.aa-empty i { margin-right: 6px; }
.aa-empty .muted { color: #a99dc0; font-size: 12px; }
.aa-link { color: #7B61FF; text-decoration: underline; }
.aa-report { background: #fff; border-radius: 12px; padding: 16px 18px; }
.aa-foot { display: flex; gap: 16px; flex-wrap: wrap; margin-top: 12px; padding-top: 10px; border-top: 1px solid #f3f0f8; font-size: 12px; color: #9a9aa0; }
.aa-foot i { margin-right: 4px; }
.aa-period { margin-left: auto; }

.aa-fade-enter-active, .aa-fade-leave-active { transition: opacity .2s; }
.aa-fade-enter-from, .aa-fade-leave-to { opacity: 0; }

/* Markdown 排版 */
.aa-md { font-size: 14px; line-height: 1.75; color: #2c2c30; }
.aa-md :deep(h1), .aa-md :deep(h2), .aa-md :deep(h3) { font-size: 15px; margin: 14px 0 8px; color: #1d1d1f; }
.aa-md :deep(p) { margin: 8px 0; }
.aa-md :deep(strong) { color: #6a3fb0; }
.aa-md :deep(ul), .aa-md :deep(ol) { padding-left: 22px; margin: 8px 0; }
.aa-md :deep(li) { margin: 4px 0; }
.aa-md :deep(table) { border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 13px; }
.aa-md :deep(th), .aa-md :deep(td) { border: 1px solid #ececf2; padding: 6px 10px; text-align: left; }
.aa-md :deep(th) { background: #f7f4fc; }
.aa-md :deep(tr:nth-child(even) td) { background: #fbfaff; }
.aa-md :deep(code) { background: #f3f0f8; border-radius: 4px; padding: 1px 5px; font-size: 12.5px; }
.aa-md :deep(blockquote) { border-left: 3px solid #d9c8f3; margin: 8px 0; padding: 2px 12px; color: #6e6e73; background: #faf7ff; }
</style>
