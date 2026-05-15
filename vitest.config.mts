import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('webgui/src', import.meta.url)),
    },
  },
  test: {
    coverage: {
      reporter: ['text', 'lcov'],
      reportsDirectory:
        process.env.SONAR_JAVASCRIPT_COVERAGE_DIR ??
        '.ai/qa/artifacts/sonar/javascript',
    },
    environment: 'node',
    include: [
      'webgui/src/**/*.test.ts',
      'tui/**/*.test.mjs',
      'docs/**/*.test.mjs',
    ],
  },
});
