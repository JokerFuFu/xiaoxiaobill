import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'
import configPrettier from 'eslint-config-prettier'
import globals from 'globals'

// ESLint 9 flat config。Phase 0 只让工具就位:噪音类问题(console/未用变量等)降为 warn,
// 不阻断 `npm run lint`(warnings 不影响退出码);逐项修复在 Phase 1。
export default [
  {
    ignores: ['dist/**', 'node_modules/**', '**/*.min.js', 'public/**'],
  },
  js.configs.recommended,
  ...pluginVue.configs['flat/recommended'],
  configPrettier,
  {
    files: ['**/*.{js,vue}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    rules: {
      'no-console': 'warn',
      'no-unused-vars': 'warn',
      'no-empty': 'warn',
      'vue/multi-word-component-names': 'off',
      'vue/require-default-prop': 'off',
    },
  },
  {
    files: ['**/__tests__/**', '**/*.spec.js'],
    languageOptions: {
      globals: { ...globals.node },
    },
  },
]
