import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api/client'

export const useMembersStore = defineStore('members', () => {
  const members = ref([])
  const loaded = ref(false)

  async function load(force = false) {
    if (loaded.value && !force) return members.value
    try {
      const r = await api.getMembers()
      members.value = r.members || []
      loaded.value = true
    } catch (e) {
      members.value = []
    }
    return members.value
  }

  async function add(name, color) {
    const r = await api.addMember(name, color)
    await load(true)
    return r.member
  }

  async function update(id, payload) {
    const r = await api.updateMember(id, payload)
    await load(true)
    return r.member
  }

  async function remove(id) {
    await api.deleteMember(id)
    await load(true)
  }

  function defaultId() {
    const self = members.value.find(m => m.is_self)
    return (self || members.value[0] || {}).id
  }

  return { members, loaded, load, add, update, remove, defaultId }
})
