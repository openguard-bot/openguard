import js from '@eslint/js'
import tseslint from 'typescript-eslint'
import astro from 'eslint-plugin-astro'
import reactHooks from 'eslint-plugin-react-hooks'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist', 'build']),
  {
    files: ['**/*.js'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
    },
    rules: {
      ...js.configs.recommended.rules,
    },
  },
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      parser: tseslint.parser,
      parserOptions: {
        project: ['./tsconfig.json'],
        ecmaVersion: 'latest',
        sourceType: 'module',
        ecmaFeatures: { jsx: true },
      },
    },
    plugins: { '@typescript-eslint': tseslint.plugin, 'react-hooks': reactHooks },
    rules: {
      ...tseslint.configs.recommended.rules,
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',
    },
  },
  {
    files: ['**/*.astro'],
    plugins: { astro },
    languageOptions: { parser: astro.parser },
    rules: {
      ...astro.configs.recommended.rules,
    },
  },
  {
    files: ['**/*.test.*'],
    languageOptions: {
      globals: {
        vi: true,
        describe: true,
        it: true,
        expect: true,
      },
    },
  },
])
