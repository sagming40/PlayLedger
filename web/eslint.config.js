import js from '@eslint/js'
import { defineConfigWithVueTs, vueTsConfigs } from '@vue/eslint-config-typescript'
import prettier from 'eslint-config-prettier/flat'
import pluginVue from 'eslint-plugin-vue'

// ESLint는 버그가 될 만한 코드를 잡고, 줄바꿈 · 따옴표 같은 모양은 Prettier에게 맡긴다
export default defineConfigWithVueTs(
  // shadcn-vue가 만들어 주는 부품은 원본과 모양을 맞춰 둔다 (.prettierignore와 같은 이유)
  { ignores: ['dist/', 'src/components/ui/'] },
  js.configs.recommended,
  pluginVue.configs['flat/recommended'],
  vueTsConfigs.recommended,
  // 맨 뒤에 둔다 ─ 앞의 설정이 켠 모양 규칙을 꺼서 Prettier와 부딪치지 않게 한다
  prettier,
)
