<template>
  <!-- 登录等 bare 页面不套侧边栏布局 -->
  <router-view v-if="bare" />
  <AppLayout v-else />
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppLayout from '@/components/AppLayout.vue'

const route = useRoute()
const bare = computed(() => route.meta.bare === true)
</script>
