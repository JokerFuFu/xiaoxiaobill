<template>
  <div class="admin-page">
    <h2><i class="fas fa-users-cog"></i> 用户管理</h2>
    <p class="desc">管理员在此创建/删除账号、重置密码。每个账号的账单数据相互隔离。</p>

    <div class="card">
      <h3>新建账号</h3>
      <div class="new-user">
        <input v-model.trim="nu.username" placeholder="用户名(登录用)" />
        <input v-model.trim="nu.display_name" placeholder="显示名(可选)" />
        <input v-model="nu.password" type="text" placeholder="初始密码(≥4位)" />
        <select v-model="nu.role">
          <option value="user">普通用户</option>
          <option value="admin">管理员</option>
        </select>
        <button @click="createUser" :disabled="busy">创建</button>
      </div>
    </div>

    <div class="card">
      <h3>账号列表（{{ users.length }}）</h3>
      <table>
        <thead><tr><th>用户名</th><th>显示名</th><th>角色</th><th>创建时间</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="u in users" :key="u.id">
            <td>{{ u.username }}</td>
            <td>{{ u.display_name }}</td>
            <td><span :class="['role', u.role]">{{ u.role === 'admin' ? '管理员' : '用户' }}</span></td>
            <td class="muted">{{ u.created_at }}</td>
            <td class="ops">
              <button class="link" @click="resetPwd(u)">重置密码</button>
              <button class="link danger" v-if="u.id !== meId" @click="removeUser(u)">删除</button>
              <span v-else class="muted">（当前账号）</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api/client'
import { useUiStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'

const ui = useUiStore()
const auth = useAuthStore()
const users = ref([])
const busy = ref(false)
const meId = ref('')
const nu = ref({ username: '', display_name: '', password: '', role: 'user' })

async function load() {
  try {
    const r = await api.adminListUsers()
    users.value = r.users || []
  } catch (e) { ui.showError('加载用户失败：' + e.message) }
}

onMounted(async () => {
  await auth.ensureLoaded()
  meId.value = auth.user?.id || ''
  await load()
})

async function createUser() {
  if (!nu.value.username || !nu.value.password) { ui.showError('用户名和密码必填'); return }
  busy.value = true
  try {
    await api.adminCreateUser({ ...nu.value })
    ui.showSuccess('账号已创建')
    nu.value = { username: '', display_name: '', password: '', role: 'user' }
    await load()
  } catch (e) { ui.showError('创建失败：' + e.message) }
  finally { busy.value = false }
}

async function removeUser(u) {
  if (!confirm(`确定删除账号「${u.username}」？该账号的账单数据不会自动删除，但将无法登录。`)) return
  try {
    await api.adminDeleteUser(u.id)
    ui.showSuccess('已删除')
    await load()
  } catch (e) { ui.showError('删除失败：' + e.message) }
}

async function resetPwd(u) {
  const p = prompt(`为「${u.username}」设置新密码(≥4位)：`)
  if (!p) return
  try {
    await api.adminResetPassword(u.id, p)
    ui.showSuccess('密码已重置')
  } catch (e) { ui.showError('重置失败：' + e.message) }
}
</script>

<style scoped>
.admin-page { padding: 24px; max-width: 900px; margin: 0 auto; }
.admin-page h2 { margin: 0 0 4px; font-size: 22px; }
.admin-page h2 i { color: #FF9500; margin-right: 8px; }
.desc { color: #6e6e73; font-size: 13px; margin-bottom: 18px; }
.card { background: #fff; border: 1px solid #eee; border-radius: 14px; padding: 18px; margin-bottom: 18px; }
.card h3 { margin: 0 0 14px; font-size: 16px; }
.new-user { display: flex; flex-wrap: wrap; gap: 10px; }
.new-user input, .new-user select { height: 38px; border: 1px solid #d2d2d7; border-radius: 8px; padding: 0 12px; font-size: 14px; }
.new-user input { flex: 1; min-width: 130px; }
.new-user button { height: 38px; padding: 0 20px; border: none; border-radius: 8px; background: #007AFF; color: #fff; cursor: pointer; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { border-bottom: 1px solid #f0f0f0; padding: 10px 8px; text-align: left; }
.muted { color: #9aa0a6; font-size: 12px; }
.role { font-size: 12px; padding: 2px 8px; border-radius: 6px; }
.role.admin { background: #FF9500; color: #fff; }
.role.user { background: #eef1f4; color: #555; }
.ops .link { background: none; border: none; color: #007AFF; cursor: pointer; margin-right: 10px; font-size: 13px; }
.ops .link.danger { color: #ff3b30; }
</style>
