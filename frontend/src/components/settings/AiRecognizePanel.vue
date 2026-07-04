<template>
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
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useUiStore } from '@/stores/ui'
import { useMembersStore } from '@/stores/members'
import api from '@/api/client'

const props = defineProps({
  members: { type: Array, required: true },
})
const emit = defineEmits(['reload-files'])

const uiStore = useUiStore()
const membersStore = useMembersStore()

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
    emit('reload-files')
  } catch (e) { uiStore.showError('导入失败: ' + (e.message || '')) }
  finally { recLoading.value = false }
}

// 初始化归属成员为默认成员;成员列表异步加载完成后再兜底设置一次,
// 保持与原 Settings.vue 中「加载成员后设置 recMember」的行为一致。
onMounted(() => {
  recMember.value = membersStore.defaultId()
})
watch(() => props.members, (list) => {
  if (!recMember.value && list && list.length) {
    recMember.value = membersStore.defaultId()
  }
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

.cfg-actions { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; margin-top: 16px; }
.save-btn {
  display: inline-flex; align-items: center; gap: 7px;
  height: 38px; padding: 0 18px; border-radius: 10px; font-size: 13.5px; cursor: pointer;
  border: none; transition: all .15s; background: #007AFF; color: #fff;
}
.save-btn:hover { background: #0a6ee0; }
.save-btn:disabled { opacity: .55; cursor: not-allowed; }
.member-select { height: 34px; border: 1px solid #d2d2d7; border-radius: 8px; padding: 0 12px; font-size: 14px; }

/* 识别区 */
.rec-grid { display: grid; grid-template-columns: 240px 1fr; gap: 14px; }
@media (max-width: 760px) { .rec-grid { grid-template-columns: 1fr; } }
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
