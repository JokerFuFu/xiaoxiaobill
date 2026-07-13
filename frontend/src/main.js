import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './assets/styles/main.css'
import { migrateLegacyStorage } from './utils/storage'

// 品牌化迁移:必须在任何 store 初始化(读 localStorage)之前执行
migrateLegacyStorage()

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')
