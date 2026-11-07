<script setup lang="ts">
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

// 개인정보 안내 (S-09, DESIGN 3.6절) ─ 가입 전에도 읽을 수 있어야 해서 로그인 없이 들어온다
const auth = useAuthStore()
const backTo = computed(() => (auth.isAuthenticated ? '/settings' : '/login'))
</script>

<template>
  <main class="mx-auto flex max-w-180 flex-col gap-6 px-5 py-10 text-[15px] leading-[1.7]">
    <RouterLink :to="backTo" class="inline-flex h-11 w-fit items-center text-sm font-semibold text-brand-text hover:underline"
      >← 돌아가기</RouterLink
    >
    <h1 class="text-3xl font-extrabold tracking-tight">개인정보 안내</h1>
    <p class="text-muted-foreground">PLAYLEDGER는 개인이 학습 목적으로 만들어 운영하는 서비스예요. 무엇을 왜 저장하는지 적어 둡니다.</p>

    <section class="flex flex-col gap-2">
      <h2 class="text-lg font-bold">저장하는 것</h2>
      <ul class="list-disc pl-5">
        <li>이메일, 닉네임 ─ 로그인과 화면 표시에 써요</li>
        <li>비밀번호 ─ 원문이 아니라 되돌릴 수 없게 변환한 값만 저장해요</li>
        <li>게임 기록 ─ 직접 입력한 제목, 구매일, 구매가, 플레이타임, 평점, 한줄평이에요</li>
        <li>
          Steam을 연결하면 Steam 계정 번호(Steam ID), Steam 이름, 마지막 동기화 시각 ─ 내 라이브러리를 가져오고 설정 화면에 보여 주는 데
          써요. 연결을 해제하면 지워지고, 가져온 게임 기록은 남아요
        </li>
        <li>로그인 유지 쿠키 ─ 14일 동안 로그인을 유지하고, 스크립트가 읽을 수 없어요</li>
        <li>화면 테마 ─ 서버가 아니라 이 브라우저에만 저장해요</li>
      </ul>
    </section>

    <section class="flex flex-col gap-2">
      <h2 class="text-lg font-bold">다른 곳으로 가는 것</h2>
      <ul class="list-disc pl-5">
        <li>입력한 내용을 다른 회사나 사람에게 넘기거나 팔지 않고, 광고에 쓰지 않아요</li>
        <li>Steam 게임을 고르면 서버가 Steam에 게임 번호만 물어봐요. 내 계정 정보는 보내지 않아요</li>
        <li>
          Steam을 연결할 때는 Steam 로그인 화면으로 가서 Steam이 직접 확인해요. 비밀번호는 PLAYLEDGER로 오지 않아요. 동기화할 때는 서버가
          Steam ID로 보유 게임 · 플레이타임 · Steam 이름을 Steam에 물어봐요
        </li>
        <li>커버 이미지는 브라우저가 Steam 서버에서 직접 받아요. 이때 Steam에 접속 IP가 전달돼요</li>
        <li>접속 IP는 비밀번호 대입을 막는 요청 제한과 서버 접속 기록에 쓰여요</li>
      </ul>
    </section>

    <section class="flex flex-col gap-2">
      <h2 class="text-lg font-bold">어디에 얼마나 남는지</h2>
      <ul class="list-disc pl-5">
        <li>서버는 Vultr의 서울 데이터센터에 있어요. 2026년 12월에 다른 호스팅으로 옮길 예정이고, 옮기면 이 안내를 고쳐요</li>
        <li>서버 접속 기록에는 접속 IP, 시각, 요청한 주소가 남아요. 일정 용량이 차면 오래된 것부터 지워져요</li>
        <li>데이터베이스는 매일 새벽 암호화한 백업을 만들고, 14일이 지난 백업은 지워요</li>
        <li>
          서버가 사라질 때를 대비해 같은 백업을 Cloudflare R2 저장소에도 14일 동안 둬요. 암호화된 채로 올려서 Cloudflare도 열어 볼 수 없어요
        </li>
      </ul>
    </section>

    <section class="flex flex-col gap-2">
      <h2 class="text-lg font-bold">지우는 방법</h2>
      <p>
        설정 화면의 <strong>계정 삭제</strong>를 누르면 계정, 게임 기록, 직접 등록한 게임이 바로 지워져요. 서버 백업에는 최대 14일 동안 남을
        수 있어요.
      </p>
    </section>

    <section class="flex flex-col gap-2">
      <h2 class="text-lg font-bold">문의</h2>
      <p>
        <a
          href="https://github.com/sagming40/PlayLedger/issues"
          target="_blank"
          rel="noopener noreferrer"
          class="font-semibold text-brand-text hover:underline"
          >GitHub 이슈</a
        >로 남겨 주세요. 공개된 곳이라 이메일 같은 개인정보는 적지 마세요.
      </p>
    </section>
  </main>
</template>
