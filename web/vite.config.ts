import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), tailwindcss()],

  // '@'를 src 폴더로 읽으라는 약속
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },

  // 개발 서버 세팅
  server: {
    proxy: {
      // /api로 시작하는 요청은 FastAPI(8001번)에 대신 요청하도록 설정
      '/api': {
        // 주소는 localhost 대신 127.0.0.1 → localhost는 IPv6(::1)로 먼저 해석되는
        // 경우가 있는데, uvicorn은 IPv4(127.0.0.1)에 떠 있어서 어긋날 가능성이 있다.
        target: 'http://127.0.0.1:8001',
        // 전달할 때 8001에서 온 요청이라는 꼬리표로 바꿔 달아준다.
        changeOrigin: true,
      }
    }
  }
})
