<template>
  <div class="account-section">
    <h2 class="section-title"><i class="fas fa-user-shield title-icon" style="color:#34C759"></i> 账号与安全</h2>
    <div class="account-card">
      <div class="acc-info">
        <div class="acc-row"><span class="acc-k">登录用户名</span><span class="acc-v">{{ authStore.user?.username || '—' }}</span></div>
        <div class="acc-row"><span class="acc-k">显示名</span><span class="acc-v">{{ authStore.user?.display_name || '—' }}</span></div>
        <div class="acc-row"><span class="acc-k">角色</span><span class="acc-v">{{ authStore.isAdmin ? '管理员' : '普通用户' }}</span></div>
      </div>

      <h3 class="acc-subtitle">修改密码</h3>
      <p v-if="authStore.user?.must_change_pw" class="acc-warn">
        <i class="fas fa-triangle-exclamation"></i> 你还在使用初始密码,强烈建议立即修改。
      </p>
      <div class="acc-form">
        <div class="acc-field">
          <label>当前密码</label>
          <input v-model="pwForm.old" type="password" autocomplete="current-password" placeholder="输入当前密码" />
        </div>
        <div class="acc-field">
          <label>新密码</label>
          <input v-model="pwForm.new1" type="password" autocomplete="new-password" placeholder="至少 4 位" />
        </div>
        <div class="acc-field">
          <label>确认新密码</label>
          <input v-model="pwForm.new2" type="password" autocomplete="new-password" placeholder="再输入一次新密码" />
        </div>
        <button class="save-btn" :disabled="pwBusy" @click="submitChangePw">
          <i class="fas fa-key"></i> {{ pwBusy ? '提交中…' : '修改密码' }}
        </button>
      </div>
      <p v-if="authStore.isAdmin" class="acc-tip">
        <i class="fas fa-circle-info"></i> 需要新增/删除账号或重置他人密码？前往 <router-link to="/admin">用户管理</router-link>。
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useSessionStore } from '@/stores/session'
import { useUiStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'
import api from '@/api/client'

const sessionStore = useSessionStore()
const uiStore = useUiStore()
const authStore = useAuthStore()

// ============ 账号:修改密码 ============
const pwForm = ref({ old: '', new1: '', new2: '' })
const pwBusy = ref(false)
async function submitChangePw() {
  if (sessionStore.isDemo) { uiStore.showError('演示模式下无法修改密码'); return }
  const { old: oldPw, new1, new2 } = pwForm.value
  if (!oldPw || !new1) { uiStore.showError('请填写当前密码和新密码'); return }
  if (new1.length < 4) { uiStore.showError('新密码至少 4 位'); return }
  if (new1 !== new2) { uiStore.showError('两次输入的新密码不一致'); return }
  if (new1 === oldPw) { uiStore.showError('新密码不能与当前密码相同'); return }
  pwBusy.value = true
  try {
    await api.changePassword(oldPw, new1)
    pwForm.value = { old: '', new1: '', new2: '' }
    await authStore.refresh()   // 刷新 must_change_pw 标志,清除安全提醒
    uiStore.showSuccess('密码已修改')
  } catch (e) {
    uiStore.showError('修改失败：' + (e.message || '请检查当前密码'))
  } finally {
    pwBusy.value = false
  }
}
</script>

<style scoped>
.section-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-color);
  margin: 0 0 16px 0;
}

/* ===== 账号 / 安全 ===== */
.account-section .section-title { display: flex; align-items: center; gap: 8px; font-size: 17px; margin-bottom: 14px; }
.account-card { max-width: 460px; background: #fff; border: 1px solid #ebebf0; border-radius: 14px; padding: 20px 22px; }
.acc-info { border-bottom: 1px solid #f0f0f4; padding-bottom: 14px; margin-bottom: 16px; }
.acc-row { display: flex; justify-content: space-between; font-size: 14px; padding: 5px 0; }
.acc-k { color: #86868b; }
.acc-v { color: #1d1d1f; font-weight: 500; }
.acc-subtitle { font-size: 15px; margin: 0 0 10px; color: #1d1d1f; }
.acc-warn {
  display: flex; align-items: center; gap: 6px; margin: 0 0 12px;
  background: #fff7e6; border: 1px solid #ffe1a8; color: #b25e00;
  font-size: 13px; padding: 8px 12px; border-radius: 8px;
}
.acc-form { display: flex; flex-direction: column; gap: 12px; }
.acc-field { display: flex; flex-direction: column; gap: 5px; }
.acc-field label { font-size: 13px; color: #6e6e73; }
.acc-field input {
  height: 40px; border: 1px solid #d2d2d7; border-radius: 9px;
  padding: 0 12px; font-size: 14px; outline: none; transition: border-color .2s;
}
.acc-field input:focus { border-color: #007AFF; }
.acc-form .save-btn { align-self: flex-start; margin-top: 4px; padding: 9px 18px; border: none; border-radius: 9px; font-size: 14px; cursor: pointer; background: #007AFF; color: #fff; display: inline-flex; align-items: center; gap: 7px; }
.acc-form .save-btn:disabled { opacity: .6; cursor: not-allowed; }
.acc-tip { margin: 16px 0 0; font-size: 12.5px; color: #86868b; }
.acc-tip a { color: #007AFF; text-decoration: none; }
</style>
