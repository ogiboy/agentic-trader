import { uninstallTarget } from './target-factory.mjs';

export function staticTargets() {
  return [
    uninstallTarget(
      'pytest-cache',
      'Pytest cache',
      '.pytest_cache',
      'artifacts',
    ),
    uninstallTarget('ruff-cache', 'Ruff cache', '.ruff_cache', 'artifacts'),
    uninstallTarget('mypy-cache', 'Mypy cache', '.mypy_cache', 'artifacts'),
    uninstallTarget('pyright-cache', 'Pyright cache', '.pyright', 'artifacts'),
    uninstallTarget(
      'coverage-file',
      'Coverage data file',
      '.coverage',
      'artifacts',
    ),
    uninstallTarget(
      'coverage-xml',
      'Coverage XML report',
      'coverage.xml',
      'artifacts',
    ),
    uninstallTarget('htmlcov', 'HTML coverage report', 'htmlcov', 'artifacts'),
    uninstallTarget(
      'build-dir',
      'Python build directory',
      'build',
      'artifacts',
    ),
    uninstallTarget('dist-dir', 'Python dist directory', 'dist', 'artifacts'),
    uninstallTarget(
      'docs-next',
      'Docs Next.js build output',
      'docs/.next',
      'artifacts',
    ),
    uninstallTarget(
      'docs-out',
      'Docs static export output',
      'docs/out',
      'artifacts',
    ),
    uninstallTarget(
      'docs-source',
      'Generated docs source cache',
      'docs/.source',
      'artifacts',
    ),
    uninstallTarget(
      'webgui-next',
      'Web GUI Next.js build output',
      'webgui/.next',
      'artifacts',
    ),
    uninstallTarget(
      'webgui-out',
      'Web GUI static output',
      'webgui/out',
      'artifacts',
    ),
    uninstallTarget(
      'tui-dist',
      'Terminal UI build output',
      'tui/dist',
      'artifacts',
    ),
    uninstallTarget(
      'camofox-dist',
      'Camofox helper dist output',
      'tools/camofox-browser/dist',
      'artifacts',
    ),
    uninstallTarget(
      'camofox-build',
      'Camofox helper build output',
      'tools/camofox-browser/build',
      'artifacts',
    ),
    uninstallTarget(
      'camofox-coverage',
      'Camofox helper coverage output',
      'tools/camofox-browser/coverage',
      'artifacts',
    ),
    uninstallTarget(
      'camofox-cache',
      'Camofox helper local cache',
      'tools/camofox-browser/.cache',
      'artifacts',
    ),
    uninstallTarget(
      'camofox-test-results',
      'Camofox helper test results',
      'tools/camofox-browser/test-results',
      'artifacts',
    ),
    uninstallTarget(
      'camofox-playwright-report',
      'Camofox helper Playwright report',
      'tools/camofox-browser/playwright-report',
      'artifacts',
    ),
    uninstallTarget('root-venv', 'Root uv Python environment', '.venv', 'deps'),
    uninstallTarget(
      'root-node-modules',
      'Root pnpm workspace dependencies',
      'node_modules',
      'deps',
    ),
    uninstallTarget(
      'docs-node-modules',
      'Docs workspace dependencies',
      'docs/node_modules',
      'deps',
    ),
    uninstallTarget(
      'webgui-node-modules',
      'Web GUI workspace dependencies',
      'webgui/node_modules',
      'deps',
    ),
    uninstallTarget(
      'tui-node-modules',
      'Terminal UI workspace dependencies',
      'tui/node_modules',
      'deps',
    ),
    uninstallTarget(
      'camofox-node-modules',
      'Camofox helper dependencies',
      'tools/camofox-browser/node_modules',
      'deps',
    ),
    uninstallTarget(
      'research-flow-venv',
      'CrewAI Flow sidecar uv environment',
      'sidecars/research_flow/.venv',
      'deps',
    ),
    uninstallTarget(
      'pnpm-store',
      'Repo-local pnpm store cache',
      '.pnpm-store',
      'deps',
    ),
    uninstallTarget(
      'model-service-state',
      'App-owned model-service state and logs',
      'runtime/model_service',
      'service-state',
      {
        blockingFiles: ['runtime/model_service/ollama_service.json'],
        reason:
          'Run pnpm run app:stop -- --model-service --yes before deleting recorded model-service state.',
      },
    ),
    uninstallTarget(
      'camofox-service-state',
      'App-owned Camofox service state and logs',
      'runtime/camofox_service',
      'service-state',
      {
        blockingFiles: ['runtime/camofox_service/camofox_service.json'],
        reason:
          'Run pnpm run app:stop -- --camofox-service --yes before deleting recorded Camofox service state.',
      },
    ),
    uninstallTarget(
      'webgui-service-state',
      'App-owned Web GUI service state and logs',
      'runtime/webgui_service',
      'service-state',
      {
        blockingFiles: ['runtime/webgui_service/webgui_service.json'],
        reason:
          'Run pnpm run app:stop -- --webgui --yes before deleting recorded Web GUI service state.',
      },
    ),
  ];
}
