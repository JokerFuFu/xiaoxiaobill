<template>
  <div class="login-wrap">
    <div class="login-card">
      <div class="login-head">
        <img src="/images/logo_128.png" alt="logo" class="login-logo" />
        <h1>小遥账单助手</h1>
        <p class="sub">隐私优先 · 多用户记账</p>
      </div>

      <!-- 全新部署引导:带出默认账号,首次进入点一下即可 -->
      <div v-if="fresh" class="fresh-tip">
        <p class="fresh-title"><i class="fas fa-hand-sparkles"></i> 首次使用</p>
        <p class="fresh-body">
          <template v-if="defaultPassword">
            已为你填入默认管理员账号 <b>{{ freshUser }} / {{ defaultPassword }}</b>，直接点「登录」即可进入。
          </template>
          <template v-else>
            默认管理员账号为 <b>{{ freshUser }}</b>，密码是你部署时设置的 <code>ADMIN_PASSWORD</code>。
          </template>
          <br />进入后请到「设置 → 账号」尽快修改密码。
        </p>
      </div>

      <form class="login-form" @submit.prevent="onLogin">
        <label>用户名</label>
        <input v-model.trim="username" type="text" placeholder="请输入用户名" autocomplete="username" />
        <label>密码</label>
        <input v-model="password" type="password" placeholder="请输入密码" autocomplete="current-password" />

        <p v-if="error" class="err">{{ error }}</p>

        <button type="submit" class="btn-primary" :disabled="loading">
          {{ loading ? '登录中…' : '登 录' }}
        </button>
      </form>

      <div class="login-foot">
        <button class="btn-ghost" @click="onDemo" :disabled="loading">先随便看看（演示数据）</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useSessionStore } from '@/stores/session'
import api from '@/api/client'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const sessionStore = useSessionStore()

// 只接受站内相对路径,防开放重定向;数组取首个
function safeRedirect() {
  let r = route.query.redirect
  if (Array.isArray(r)) r = r[0]
  return (typeof r === 'string' && r.startsWith('/') && !r.startsWith('//')) ? r : '/'
}

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

// 首次安装引导:全新部署且管理员仍用初始口令时,带出默认账号方便进入
const fresh = ref(false)
const freshUser = ref('admin')
const defaultPassword = ref('')

onMounted(async () => {
  try {
    const r = await api.authBootstrap()
    if (r && r.fresh) {
      fresh.value = true
      freshUser.value = r.username || 'admin'
      username.value = r.username || 'admin'
      if (r.default_password) {
        defaultPassword.value = r.default_password
        password.value = r.default_password
      }
    }
  } catch (e) { /* 引导信息拿不到不影响正常登录 */ }
})

async function onLogin() {
  if (!username.value || !password.value) { error.value = '请输入用户名和密码'; return }
  error.value = ''
  loading.value = true
  try {
    await auth.login(username.value, password.value)
    router.replace(safeRedirect())
  } catch (e) {
    error.value = e.message || '登录失败'
  } finally {
    loading.value = false
  }
}

async function onDemo() {
  loading.value = true
  try {
    // 用 session store 进入演示(同时写 isDemo+localStorage),再刷新 auth 态,二者一致
    await sessionStore.enterDemoMode()
    await auth.refresh()
    router.replace('/')
  } catch (e) {
    error.value = '进入演示失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrap {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f5f7fa 0%, #e8eef5 100%);
  padding: 20px;
}
.login-card {
  width: 100%;
  max-width: 380px;
  background: #fff;
  border-radius: 18px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.08);
  padding: 36px 32px 28px;
}
.login-head { text-align: center; margin-bottom: 24px; }
.login-logo { width: 72px; height: 72px; object-fit: contain; }
.login-head h1 { font-size: 22px; margin: 8px 0 2px; color: #1d1d1f; }
.login-head .sub { color: #86868b; font-size: 13px; margin: 0; }
.fresh-tip {
  background: #f0f7ff; border: 1px solid #cfe4ff; border-radius: 10px;
  padding: 12px 14px; margin-bottom: 4px;
}
.fresh-title { margin: 0 0 4px; font-size: 13px; font-weight: 600; color: #007AFF; }
.fresh-body { margin: 0; font-size: 12.5px; line-height: 1.6; color: #4a5568; }
.fresh-body b { color: #1d1d1f; }
.fresh-body code { background: #e3edf9; padding: 1px 5px; border-radius: 4px; font-size: 12px; }
.login-form { display: flex; flex-direction: column; }
.login-form label { font-size: 13px; color: #6e6e73; margin: 12px 0 6px; }
.login-form input {
  height: 44px; border: 1px solid #d2d2d7; border-radius: 10px;
  padding: 0 14px; font-size: 15px; outline: none; transition: border-color .2s;
}
.login-form input:focus { border-color: #007AFF; }
.err { color: #ff3b30; font-size: 13px; margin: 12px 0 0; }
.btn-primary {
  margin-top: 22px; height: 46px; border: none; border-radius: 10px;
  background: #007AFF; color: #fff; font-size: 16px; font-weight: 500; cursor: pointer;
  transition: opacity .2s;
}
.btn-primary:disabled { opacity: .6; cursor: not-allowed; }
.login-foot { text-align: center; margin-top: 18px; }
.btn-ghost { background: none; border: none; color: #86868b; font-size: 13px; cursor: pointer; }
.btn-ghost:hover { color: #007AFF; }
</style>
