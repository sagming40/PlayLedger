<script setup lang="ts">
import { ref, onMounted } from 'vue'

// ref = 값이 바뀌면 화면이 자동으로 따라가 바뀌는 상자
// 그냥 변수에 담으면 값이 바뀌어도 Vue 인지하지 못한다.
const status = ref('확인 중...')

// onMounted = 화면이 처음 그려진 직후에 최초 1회만 실행되는 자리
onMounted(async () => {
  try {
    // 주소에 port가 들어있지 않다.
    // Browser는 5173(우리 집)에 물어본다 생각하고,
    // Vite 개발 서버가 그 요청을 8001로 대신 전달한다.
    const res = await fetch('/api/health')
    const data = await res.json()
    status.value = data.status
  } catch (e) {
    // 서버가 꺼져 있거나 proxy가 풀렸을 때 화면이 "확인 중..."에
    // 멈춰 있으면 원인을 알 수 없으므로 실패도 화면에 드러낸다.
    status.value = '연결 실패'
  }
})
</script>

<template>
  <!-- 
       Tailwind는 class 이름 하나가 CSS 한 줄에 대응한다.
       min-h-screen = 최소 높이를 회면 전체로
       flex flex-col items-center justify-center = 세로로 쌓고 가운데 정렬
       gap-2 = Element 사이 간격 
  -->
  <div class="min-h-screen flex flex-col items-center justify-center gap-2">     
    <h1 class="text-3xl font-bold">PLAYLEDGER</h1>
    <p class="text-slate-500">API 상태: {{ status }}</p>
  </div>
</template>
