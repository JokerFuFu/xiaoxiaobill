<template>
  <!-- 从邮箱导入账单(通用 IMAP) -->
  <div class="ai-section">
    <h2 class="section-title"><i class="fas fa-envelope-open-text title-icon" style="color:#007AFF"></i> 从邮箱导入账单</h2>
    <div class="ai-card">
      <p class="ai-desc">
        把支付宝/微信/银行账单定期发到你的邮箱,这里一键拉取并导入。支持任意 <strong>IMAP 邮箱</strong>(QQ/163/Gmail/Outlook…或自定义服务器),
        登录用<strong>授权码</strong>(不是登录密码)。配置只存在<strong>你自己的账号</strong>里。
        <span v-if="mailCfg.has_auth" class="cfg-badge custom">已配置 · {{ mailCfg.address }}</span>
        <span v-else class="cfg-badge default">未配置</span>
      </p>

      <!-- 服务商预设 -->
      <div class="provider-row">
        <button
          v-for="p in mailCfg.presets" :key="p.name"
          class="provider-chip" :class="{ active: mailForm.host === p.host }"
          @click="applyMailPreset(p)"
        >{{ p.name }}</button>
        <button class="provider-chip add-chip" :class="{ active: mailCustom }" @click="mailCustom = !mailCustom">
          <i class="fas fa-server"></i> 自定义
        </button>
      </div>
      <p v-if="mailHelp" class="muted" style="margin:0 0 12px"><i class="fas fa-circle-info"></i> {{ mailHelp }}</p>

      <div class="cfg-grid">
        <div class="cfg-field">
          <label>邮箱地址</label>
          <input v-model.trim="mailForm.address" placeholder="如 xxx@qq.com" />
        </div>
        <div class="cfg-field">
          <label>授权码 <span class="muted" v-if="mailCfg.has_auth">(已保存,留空表示不修改)</span></label>
          <input v-model="mailForm.auth_code" type="password" placeholder="IMAP 授权码/应用专用密码" autocomplete="off" />
        </div>
        <template v-if="mailCustom">
          <div class="cfg-field">
            <label>IMAP 服务器</label>
            <input v-model.trim="mailForm.host" placeholder="如 imap.example.com" />
          </div>
          <div class="cfg-field">
            <label>端口(SSL)</label>
            <input v-model.number="mailForm.port" type="number" placeholder="993" />
          </div>
        </template>
      </div>

      <div class="cfg-actions">
        <button class="save-btn" @click="saveMailConfig" :disabled="!!mailBusy">
          <i class="fas fa-check"></i> 保存配置
        </button>
        <button class="test-btn" @click="testMail" :disabled="!!mailBusy">
          <i class="fas fa-plug"></i> {{ mailBusy === 'test' ? '测试中…' : '测试连接' }}
        </button>
        <button v-if="mailCfg.has_auth" class="reset-btn" @click="clearMailAuth" :disabled="!!mailBusy">清除授权码</button>
        <span v-if="mailTestMsg" class="test-result" :class="{ ok: mailTestOk }">
          <i :class="mailTestOk ? 'fas fa-circle-check' : 'fas fa-circle-xmark'"></i> {{ mailTestMsg }}
        </span>
      </div>

      <div class="cfg-actions" style="margin-top:8px">
        <label class="switch">
          <input type="checkbox" v-model="mailAutoImport" :disabled="!mailCfg.has_auth" @change="toggleAutoImport" />
          <span class="slider"></span>
        </label>
        <span>{{ mailAutoImport ? '自动导入已开启' : '自动导入已关闭' }}</span>
        <span v-if="mailCfg.pending_count" class="cfg-badge custom">{{ mailCfg.pending_count }} 封待导入(需要密码)</span>
        <span v-if="mailCfg.last_error" class="test-result">
          <i class="fas fa-circle-xmark"></i> 自动同步失败:{{ mailCfg.last_error }}
        </span>
        <span v-else-if="mailCfg.last_success_at" class="muted">上次自动同步:{{ mailCfg.last_success_at }}</span>
      </div>

      <!-- 拉取与导入 -->
      <div class="mail-fetch-bar">
        <label>拉取近</label>
        <select v-model.number="mailDays" class="member-select">
          <option :value="30">30 天</option>
          <option :value="90">90 天</option>
          <option :value="180">180 天</option>
          <option :value="365">一年</option>
        </select>
        <button class="save-btn" @click="fetchMails" :disabled="!mailCfg.has_auth || mailBusy === 'fetch'">
          <i class="fas fa-cloud-arrow-down"></i> {{ mailBusy === 'fetch' ? '正在搜索邮箱…' : '拉取账单邮件' }}
        </button>
        <span class="muted">附件导入后归属上方选择的成员;加密压缩包(支付宝/微信)需填邮件里给的解压密码</span>
      </div>

      <div v-if="mailFetched && !mails.length" class="muted" style="padding:10px 2px">
        没有找到带账单附件的邮件。确认账单邮件在「收件箱」里(不在垃圾箱/其他文件夹),或扩大时间范围。
      </div>
      <div v-if="mails.length" class="mail-list">
        <div v-for="m in mails" :key="m.uid" class="mail-item">
          <div class="mail-head">
            <span class="mail-subject">{{ m.subject }}</span>
            <span class="mail-meta">{{ m.sender }} · {{ m.date }}</span>
          </div>
          <div v-for="a in m.attachments" :key="a.index" class="mail-att">
            <i :class="a.is_zip ? 'fas fa-file-zipper' : 'fas fa-file-lines'"></i>
            <span class="att-name">{{ a.filename }}</span>
            <span class="att-size">{{ fmtSize(a.size) }}</span>
            <span v-if="a.needs_password" class="cfg-badge default">需要密码</span>
            <input
              v-if="a.is_zip || a.needs_password || a.filename.toLowerCase().endsWith('.pdf')"
              v-model="zipPwd[m.uid + ':' + a.index]"
              class="att-pwd" placeholder="解压/打开密码(如有)" autocomplete="off"
            />
            <button
              class="member-add-btn" :disabled="mailBusy === 'import'"
              @click="importAtt(m, a)"
            >{{ importedHint(m) ? '再次导入' : '导入' }}</button>
            <span v-if="importedHint(m)" class="att-done"><i class="fas fa-circle-check"></i> 已导入</span>
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

const props = defineProps({
  uploadMember: { type: [String, Number], default: '' },
})
const emit = defineEmits(['reload-files'])

const uiStore = useUiStore()

const mailCfg = ref({ host: '', port: 993, address: '', has_auth: false, presets: [],
                       auto_import: false, pending_count: 0, last_run_at: '', last_success_at: '', last_error: '' })
const mailForm = ref({ host: '', port: 993, address: '', auth_code: '' })
const mailAutoImport = ref(false)
const mailCustom = ref(false)
const mailBusy = ref('')
const mailTestMsg = ref('')
const mailTestOk = ref(false)
const mailDays = ref(90)
const mails = ref([])
const mailFetched = ref(false)
const zipPwd = ref({})

const mailHelp = computed(() => {
  const hit = (mailCfg.value.presets || []).find(p => p.host === mailForm.value.host)
  return hit?.help || ''
})

function applyMailPreset(p) {
  mailForm.value.host = p.host
  mailForm.value.port = p.port
  mailCustom.value = false
  mailTestMsg.value = ''
}

function fmtSize(n) {
  if (n == null) return ''
  if (n > 1024 * 1024) return (n / 1024 / 1024).toFixed(1) + ' MB'
  if (n > 1024) return Math.round(n / 1024) + ' KB'
  return n + ' B'
}

async function loadMailConfig() {
  try {
    const r = await api.mailGetConfig()
    mailCfg.value = r.config
    mailForm.value.host = r.config.host || ''
    mailForm.value.port = r.config.port || 993
    mailForm.value.address = r.config.address || ''
    mailForm.value.auth_code = ''
    mailAutoImport.value = !!r.config.auto_import
  } catch (e) { /* 未登录等场景忽略 */ }
}

async function toggleAutoImport() {
  const next = mailAutoImport.value
  try {
    const r = await api.mailSaveConfig({ auto_import: next })
    mailCfg.value = r.config
    uiStore.showSuccess(next ? '已开启自动导入' : '已关闭自动导入')
  } catch (e) {
    mailAutoImport.value = !next
    uiStore.showError(e.message || '设置失败')
  }
}

async function saveMailConfig() {
  const f = mailForm.value
  if (!f.host || !f.address) { uiStore.showError('请选择邮箱服务商并填写邮箱地址'); return }
  mailBusy.value = 'save'
  try {
    const payload = { host: f.host, port: f.port || 993, address: f.address }
    if (f.auth_code) payload.auth_code = f.auth_code
    const r = await api.mailSaveConfig(payload)
    mailCfg.value = r.config
    mailForm.value.auth_code = ''
    uiStore.showSuccess('邮箱配置已保存')
  } catch (e) { uiStore.showError('保存失败: ' + e.message) }
  finally { mailBusy.value = '' }
}

async function testMail() {
  mailBusy.value = 'test'; mailTestMsg.value = ''
  try {
    if (mailForm.value.auth_code || !mailCfg.value.has_auth) await saveMailConfigQuiet()
    const r = await api.mailTest()
    mailTestOk.value = !!r.ok
    mailTestMsg.value = r.message
  } catch (e) { mailTestOk.value = false; mailTestMsg.value = e.message || '测试失败' }
  finally { mailBusy.value = '' }
}

async function saveMailConfigQuiet() {
  const f = mailForm.value
  if (!f.host || !f.address) throw new Error('请先填写邮箱地址与授权码')
  const payload = { host: f.host, port: f.port || 993, address: f.address }
  if (f.auth_code) payload.auth_code = f.auth_code
  const r = await api.mailSaveConfig(payload)
  mailCfg.value = r.config
  mailForm.value.auth_code = ''
}

async function clearMailAuth() {
  if (!confirm('清除已保存的授权码？')) return
  try {
    const r = await api.mailSaveConfig({ auth_code: '' })
    mailCfg.value = r.config
    uiStore.showSuccess('已清除授权码')
  } catch (e) { uiStore.showError(e.message) }
}

async function fetchMails() {
  mailBusy.value = 'fetch'; mails.value = []; mailFetched.value = false
  try {
    const r = await api.mailFetch(mailDays.value)
    mails.value = r.mails || []
    mailFetched.value = true
    if (mails.value.length) uiStore.showSuccess(`找到 ${mails.value.length} 封账单邮件`)
  } catch (e) { uiStore.showError(e.message || '拉取失败') }
  finally { mailBusy.value = '' }
}

function importedHint(m) {
  return (m.imported_files || []).length > 0
}

async function importAtt(m, a) {
  mailBusy.value = 'import'
  try {
    const r = await api.mailImport({
      uid: m.uid, index: a.index,
      zip_password: zipPwd.value[m.uid + ':' + a.index] || '',
      member_id: props.uploadMember || ''
    })
    m.imported_files = [...new Set([...(m.imported_files || []), ...(r.files || [])])]
    uiStore.showSuccess(`已导入 ${r.files.length} 个账单文件: ${r.files.join('、')}`)
    emit('reload-files')
  } catch (e) { uiStore.showError(e.message || '导入失败') }
  finally { mailBusy.value = '' }
}

onMounted(async () => {
  await loadMailConfig()
})
</script>

<style scoped>
/* ===== AI 配置 / 智能识别 区块(共用外壳) ===== */
.ai-section { margin: 26px 0; }
.ai-section .section-title { display: flex; align-items: center; gap: 8px; font-size: 17px; margin-bottom: 12px; }
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
.add-chip { color: #007AFF; border-style: dashed; }

.cfg-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px 16px; }
.cfg-field { display: flex; flex-direction: column; }
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

.member-select { height: 34px; border: 1px solid #d2d2d7; border-radius: 8px; padding: 0 12px; font-size: 14px; }
.member-add-btn { height: 32px; padding: 0 14px; border: none; border-radius: 8px; background: #007AFF; color: #fff; cursor: pointer; font-size: 13px; }

/* 开关 */
.switch { position: relative; display: inline-block; width: 44px; height: 24px; }
.switch input { opacity: 0; width: 0; height: 0; }
.slider { position: absolute; inset: 0; background: #d6d6dc; border-radius: 24px; transition: .2s; cursor: pointer; }
.slider::before { content: ''; position: absolute; height: 18px; width: 18px; left: 3px; top: 3px; background: #fff; border-radius: 50%; transition: .2s; }
.switch input:checked + .slider { background: #34C759; }
.switch input:checked + .slider::before { transform: translateX(20px); }

/* ===== 邮箱取账单 ===== */
.mail-fetch-bar {
  display: flex; align-items: center; flex-wrap: wrap; gap: 10px;
  border-top: 1px solid #f0f0f4; margin-top: 16px; padding-top: 14px;
}
.mail-fetch-bar > label { font-size: 13px; color: #4a4a4f; }
.mail-list { margin-top: 14px; display: flex; flex-direction: column; gap: 10px; }
.mail-item { border: 1px solid #ebebf0; border-radius: 12px; padding: 12px 14px; background: #fff; }
.mail-head { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; flex-wrap: wrap; margin-bottom: 8px; }
.mail-subject { font-size: 14px; font-weight: 600; color: #1d1d1f; }
.mail-meta { font-size: 12px; color: #9aa0a6; }
.mail-att {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  padding: 7px 10px; border-radius: 9px; background: #f8fafc; margin-top: 6px;
}
.mail-att > i { color: #007AFF; }
.att-name { font-size: 13px; color: #3a3a3c; word-break: break-all; flex: 1; min-width: 160px; }
.att-size { font-size: 12px; color: #9aa0a6; white-space: nowrap; }
.att-pwd {
  height: 30px; width: 140px; border: 1px solid #e2c08d; border-radius: 8px;
  padding: 0 10px; font-size: 12.5px; outline: none; background: #fffdf5;
}
.att-pwd:focus { border-color: #FF9500; }
.att-done { font-size: 12px; color: #1d8a44; white-space: nowrap; }
.att-done i { margin-right: 3px; }
</style>
