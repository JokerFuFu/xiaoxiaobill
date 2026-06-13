import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    port: 3000,
    proxy: {
      // 开发时代理 API 请求到 Flask 后端
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    chunkSizeWarningLimit: 1200,
    rollupOptions: {
      output: {
        // 把大体积第三方库拆成独立 chunk:内容稳定,部署应用代码后浏览器仍能命中缓存,
        // 不必每次重新下载 ~1MB 的 echarts
        manualChunks: {
          echarts: ['echarts'],
          markdown: ['marked', 'dompurify'],
        }
      }
    }
  }
})
