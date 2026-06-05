import nextVitals from 'eslint-config-next/core-web-vitals';
import nextTs from 'eslint-config-next/typescript';
import eslintConfigPrettier from 'eslint-config-prettier/flat';
import { defineConfig, globalIgnores } from 'eslint/config';

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  eslintConfigPrettier,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    '.next/**',
    'out/**',
    'build/**',
    'next-env.d.ts',
    '../.agents/**',
    '../.claude/**',
    '../.claude-flow/**',
    '../CLAUDE.md',
    '../skills-lock.json',
  ]),
  {
    settings: {
      react: { version: '19' },
    },
  },
]);

export default eslintConfig;
