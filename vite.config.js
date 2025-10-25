import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath, URL } from 'node:url' // [新增] 导入 Node.js 的 URL 模块

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],

  // [新增] 添加 resolve.alias 配置
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  }
})