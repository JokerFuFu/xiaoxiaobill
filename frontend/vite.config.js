import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// https://vitejs.dev/config/
export default defineConfig(({ command }) => ({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  // 生产构建剔除 console/debugger(仅 build 生效,dev 保留调试输出)
  esbuild: command === 'build' ? { drop: ['console', 'debugger'] } : {},
  server: {
    port: 3000,
    proxy: {
      // 开发时代理 API 请求到 Flask 后端
      // 用 127.0.0.1 而非 localhost:macOS 上 node 会把 localhost 解析为 ::1,
      // 撞上 AirPlay Receiver 占用的 IPv6 5000 端口
      '/api': {
        target: 'http://127.0.0.1:5000',
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
}))
