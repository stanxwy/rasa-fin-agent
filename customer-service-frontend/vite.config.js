import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq) => {
            // 对 /api/v1 开头的金融API注入默认请求头
            if (proxyReq.path.startsWith('/api/v1')) {
              if (!proxyReq.hasHeader('X-Channel-Code')) {
                proxyReq.setHeader('X-Channel-Code', 'mobile_bank')
              }
              if (!proxyReq.hasHeader('Authorization')) {
                // 默认使用 sender_id 作为 Bearer token，实际调用时会覆盖
                proxyReq.setHeader('Authorization', 'Bearer CUS0000001')
              }
            }
          })
        },
      },
      '/commerce': {
        target: 'http://127.0.0.1:18081',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/commerce/, ''),
      },
      '/health': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
