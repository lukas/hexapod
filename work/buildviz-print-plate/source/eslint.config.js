import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

// Import boundaries between the pieces (see plans/repo-split.md):
//   cli    -> hub, checks, core
//   hub    -> checks (pack-export only), core
//   viewer -> checks, core        (viewer/src; vite.config.ts is build tooling)
//   checks -> core
//   core   -> (nothing internal)
const forbid = (...dirs) => ({
  patterns: dirs.map((dir) => ({
    group: [`**/${dir}/**`],
    message: `This piece must not import from ${dir}/ (see plans/repo-split.md).`,
  })),
})

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
    },
  },
  {
    files: ['core/**/*.ts'],
    rules: { 'no-restricted-imports': ['error', forbid('checks', 'hub', 'cli', 'viewer')] },
  },
  {
    files: ['checks/**/*.ts'],
    rules: { 'no-restricted-imports': ['error', forbid('hub', 'cli', 'viewer')] },
  },
  {
    files: ['hub/**/*.ts'],
    rules: { 'no-restricted-imports': ['error', forbid('cli', 'viewer')] },
  },
  {
    files: ['viewer/src/**/*.{ts,tsx}'],
    rules: { 'no-restricted-imports': ['error', forbid('hub', 'cli')] },
  },
  {
    files: ['cli/**/*.ts'],
    rules: { 'no-restricted-imports': ['error', forbid('viewer')] },
  },
])
