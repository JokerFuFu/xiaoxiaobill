<template>
  <!-- 成员维度：上传归属 + 成员管理 -->
  <div class="member-panel">
    <div class="member-row">
      <label><i class="fas fa-user-tag"></i> 本次上传归属成员：</label>
      <select
        class="member-select"
        :value="uploadMember"
        @change="$emit('update:uploadMember', $event.target.value)"
      >
        <option v-for="m in members" :key="m.id" :value="m.id">{{ m.name }}</option>
      </select>
      <span class="member-tip">上传的账单会整份记到该成员名下（每份导出对应一个人的账户）</span>
    </div>
    <div class="member-row">
      <label>成员：</label>
      <span v-for="m in members" :key="m.id" class="member-chip" :style="{ borderColor: m.color }">
        <span class="dot" :style="{ background: m.color }"></span>{{ m.name }}
        <i v-if="!m.is_self" class="fas fa-times del" @click="deleteMember(m)"></i>
      </span>
      <input v-model="newMemberName" class="member-add-input" placeholder="新增成员名" @keyup.enter="addMember" />
      <button class="member-add-btn" @click="addMember">+ 添加</button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useUiStore } from '@/stores/ui'
import { useMembersStore } from '@/stores/members'

defineProps({
  members: { type: Array, required: true },
  uploadMember: { type: [String, Number], default: '' },
})
const emit = defineEmits(['update:uploadMember', 'members-changed', 'members-changed-with-files'])

const uiStore = useUiStore()
const membersStore = useMembersStore()

const newMemberName = ref('')

async function addMember() {
  const name = newMemberName.value.trim()
  if (!name) return
  try {
    await membersStore.add(name)
    newMemberName.value = ''
    emit('members-changed')
    uiStore.showSuccess('成员已添加')
  } catch (e) { uiStore.showError('添加失败: ' + e.message) }
}

async function deleteMember(m) {
  if (m.is_self) { uiStore.showError('不能删除「本人」'); return }
  if (!confirm(`删除成员「${m.name}」？其名下账单会回落到默认成员。`)) return
  try {
    await membersStore.remove(m.id)
    emit('members-changed-with-files')
    uiStore.showSuccess('成员已删除')
  } catch (e) { uiStore.showError('删除失败: ' + e.message) }
}
</script>

<style scoped>
/* 成员维度面板 */
.member-panel {
  background: var(--card-bg, #fff);
  border: 1px solid var(--border-color, #eee);
  border-radius: 14px;
  padding: 16px 18px;
  margin-bottom: 18px;
}
.member-row { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; }
.member-row + .member-row { margin-top: 12px; }
.member-row > label { font-size: 14px; color: var(--text-color, #333); font-weight: 500; }
.member-select { height: 34px; border: 1px solid #d2d2d7; border-radius: 8px; padding: 0 12px; font-size: 14px; }
.member-tip { font-size: 12px; color: #9aa0a6; }
.member-chip {
  display: inline-flex; align-items: center; gap: 6px;
  border: 1px solid #d2d2d7; border-radius: 16px; padding: 4px 12px; font-size: 13px;
}
.member-chip .dot { width: 8px; height: 8px; border-radius: 50%; }
.member-chip .del { color: #c0c0c0; cursor: pointer; margin-left: 2px; }
.member-chip .del:hover { color: #ff3b30; }
.member-add-input { height: 32px; border: 1px solid #d2d2d7; border-radius: 8px; padding: 0 10px; font-size: 13px; width: 120px; }
.member-add-btn { height: 32px; padding: 0 14px; border: none; border-radius: 8px; background: #007AFF; color: #fff; cursor: pointer; font-size: 13px; }
</style>
