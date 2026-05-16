#!/usr/bin/env node
import { existsSync, readdirSync, rmSync, statSync } from 'node:fs';
import { dirname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const DEFAULT_ROOT_DIR = join(dirname(fileURLToPath(import.meta.url)), '..');
const ROOT_DIR = resolve(process.env.AGENTIC_TRADER_APP_UNINSTALL_ROOT ?? DEFAULT_ROOT_DIR);
const SCOPE_IDS = ['artifacts', 'deps', 'service-state'];

function usage(exitCode = 0) {
  process.stdout.write(`Usage: node scripts/app-uninstall.mjs [options]

Plan or run the conservative app-owned uninstall lifecycle slice.

Default behavior is a dry-run plan. Removing local files requires selecting one
or more scopes plus --yes.

Options:
  --artifacts      Remove generated build, test, and cache artifacts.
  --deps           Remove local dependency directories and local pnpm store.
  --service-state  Remove app-owned service log/state directories only when no
                   recorded service state file remains.
  --all            Select every uninstall scope.
  --yes            Approve the selected uninstall action.
  --dry-run        Print the uninstall plan without removing files.
  --json           Emit a machine-readable summary.
  -h, --help       Show this help.
`);
  process.exit(exitCode);
}

function parseArgs(argv) {
  const options = {
    dryRun: false,
    json: false,
    selectedScopes: new Set(),
    yes: false,
  };

  for (const arg of argv) {
    if (arg === '--') {
      continue;
    } else if (arg === '--artifacts') {
      options.selectedScopes.add('artifacts');
    } else if (arg === '--deps') {
      options.selectedScopes.add('deps');
    } else if (arg === '--service-state') {
      options.selectedScopes.add('service-state');
    } else if (arg === '--all') {
      for (const scope of SCOPE_IDS) {
        options.selectedScopes.add(scope);
      }
    } else if (arg === '--yes') {
      options.yes = true;
    } else if (arg === '--dry-run') {
      options.dryRun = true;
    } else if (arg === '--json') {
      options.json = true;
    } else if (arg === '-h' || arg === '--help') {
      usage(0);
    } else {
      process.stderr.write(`Unknown option: ${arg}\n`);
      usage(2);
    }
  }

  if (options.yes && !options.dryRun && options.selectedScopes.size === 0) {
    process.stderr.write('Select at least one uninstall scope before using --yes.\n');
    usage(2);
  }

  return options;
}

function rootLooksLikeAgenticTrader(rootDir) {
  return existsSync(join(rootDir, 'package.json')) && existsSync(join(rootDir, 'pyproject.toml'));
}

function assertSafeRoot(rootDir) {
  if (!rootLooksLikeAgenticTrader(rootDir)) {
    process.stderr.write(
      `Refusing to uninstall from ${rootDir}: expected package.json and pyproject.toml markers.\n`,
    );
    process.exit(2);
  }
}

function relativeTarget(path) {
  const rel = relative(ROOT_DIR, path);
  return rel === '' ? '.' : rel;
}

function targetPath(relativePath) {
  const resolvedPath = resolve(ROOT_DIR, relativePath);
  const rootWithSep = ROOT_DIR.endsWith(sep) ? ROOT_DIR : `${ROOT_DIR}${sep}`;
  if (resolvedPath !== ROOT_DIR && !resolvedPath.startsWith(rootWithSep)) {
    throw new Error(`Refusing to target path outside app root: ${relativePath}`);
  }
  return resolvedPath;
}

function uninstallTarget(id, label, relativePath, scope, options = {}) {
  const path = targetPath(relativePath);
  return {
    id,
    label,
    path,
    relative_path: relativeTarget(path),
    scope,
    mutates: true,
    selected: false,
    reason: options.reason,
    blocking_files: (options.blockingFiles ?? []).map((blockingFile) => {
      const blockingPath = targetPath(blockingFile);
      return {
        path: blockingPath,
        relative_path: relativeTarget(blockingPath),
      };
    }),
  };
}

function uninstallTargetGroup(id, label, relativePaths, scope) {
  const paths = relativePaths.map((relativePath) => targetPath(relativePath));
  return {
    id,
    label,
    path: null,
    relative_path: `${relativePaths.length} discovered ${label.toLowerCase()}`,
    paths,
    relative_paths: paths.map((path) => relativeTarget(path)),
    scope,
    mutates: true,
    selected: false,
    blocking_files: [],
  };
}

function staticTargets() {
  return [
    uninstallTarget('pytest-cache', 'Pytest cache', '.pytest_cache', 'artifacts'),
    uninstallTarget('ruff-cache', 'Ruff cache', '.ruff_cache', 'artifacts'),
    uninstallTarget('mypy-cache', 'Mypy cache', '.mypy_cache', 'artifacts'),
    uninstallTarget('pyright-cache', 'Pyright cache', '.pyright', 'artifacts'),
    uninstallTarget('coverage-file', 'Coverage data file', '.coverage', 'artifacts'),
    uninstallTarget('coverage-xml', 'Coverage XML report', 'coverage.xml', 'artifacts'),
    uninstallTarget('htmlcov', 'HTML coverage report', 'htmlcov', 'artifacts'),
    uninstallTarget('build-dir', 'Python build directory', 'build', 'artifacts'),
    uninstallTarget('dist-dir', 'Python dist directory', 'dist', 'artifacts'),
    uninstallTarget('docs-next', 'Docs Next.js build output', 'docs/.next', 'artifacts'),
    uninstallTarget('docs-out', 'Docs static export output', 'docs/out', 'artifacts'),
    uninstallTarget('docs-source', 'Generated docs source cache', 'docs/.source', 'artifacts'),
    uninstallTarget('webgui-next', 'Web GUI Next.js build output', 'webgui/.next', 'artifacts'),
    uninstallTarget('webgui-out', 'Web GUI static output', 'webgui/out', 'artifacts'),
    uninstallTarget('tui-dist', 'Terminal UI build output', 'tui/dist', 'artifacts'),
    uninstallTarget('camofox-dist', 'Camofox helper dist output', 'tools/camofox-browser/dist', 'artifacts'),
    uninstallTarget('camofox-build', 'Camofox helper build output', 'tools/camofox-browser/build', 'artifacts'),
    uninstallTarget('camofox-coverage', 'Camofox helper coverage output', 'tools/camofox-browser/coverage', 'artifacts'),
    uninstallTarget('camofox-cache', 'Camofox helper local cache', 'tools/camofox-browser/.cache', 'artifacts'),
    uninstallTarget('camofox-test-results', 'Camofox helper test results', 'tools/camofox-browser/test-results', 'artifacts'),
    uninstallTarget('camofox-playwright-report', 'Camofox helper Playwright report', 'tools/camofox-browser/playwright-report', 'artifacts'),
    uninstallTarget('root-venv', 'Root uv Python environment', '.venv', 'deps'),
    uninstallTarget('root-node-modules', 'Root pnpm workspace dependencies', 'node_modules', 'deps'),
    uninstallTarget('docs-node-modules', 'Docs workspace dependencies', 'docs/node_modules', 'deps'),
    uninstallTarget('webgui-node-modules', 'Web GUI workspace dependencies', 'webgui/node_modules', 'deps'),
    uninstallTarget('tui-node-modules', 'Terminal UI workspace dependencies', 'tui/node_modules', 'deps'),
    uninstallTarget('camofox-node-modules', 'Camofox helper dependencies', 'tools/camofox-browser/node_modules', 'deps'),
    uninstallTarget('research-flow-venv', 'CrewAI Flow sidecar uv environment', 'sidecars/research_flow/.venv', 'deps'),
    uninstallTarget('pnpm-store', 'Repo-local pnpm store cache', '.pnpm-store', 'deps'),
    uninstallTarget(
      'model-service-state',
      'App-owned model-service state and logs',
      'runtime/model_service',
      'service-state',
      {
        blockingFiles: ['runtime/model_service/ollama_service.json'],
        reason: 'Run pnpm run app:stop -- --model-service --yes before deleting recorded model-service state.',
      },
    ),
    uninstallTarget(
      'camofox-service-state',
      'App-owned Camofox service state and logs',
      'runtime/camofox_service',
      'service-state',
      {
        blockingFiles: ['runtime/camofox_service/camofox_service.json'],
        reason: 'Run pnpm run app:stop -- --camofox-service --yes before deleting recorded Camofox service state.',
      },
    ),
    uninstallTarget(
      'webgui-service-state',
      'App-owned Web GUI service state and logs',
      'runtime/webgui_service',
      'service-state',
      {
        blockingFiles: ['runtime/webgui_service/webgui_service.json'],
        reason: 'Run pnpm run app:stop -- --webgui --yes before deleting recorded Web GUI service state.',
      },
    ),
  ];
}

function shouldPrune(path) {
  const rel = relativeTarget(path);
  return [
    '.git',
    '.venv',
    'node_modules',
    '.pnpm-store',
    'docs/node_modules',
    'docs/.next',
    'docs/out',
    'docs/.source',
    'webgui/node_modules',
    'webgui/.next',
    'webgui/out',
    'tui/node_modules',
    'tui/dist',
    'tools/camofox-browser/node_modules',
    'tools/camofox-browser/dist',
    'tools/camofox-browser/build',
    'tools/camofox-browser/coverage',
    'tools/camofox-browser/.cache',
    'tools/camofox-browser/test-results',
    'tools/camofox-browser/playwright-report',
    'sidecars/research_flow/.venv',
  ].includes(rel);
}

function discoverDynamicTargets() {
  const pycachePaths = [];
  const eggInfoPaths = [];

  function walk(dir) {
    let entries;
    try {
      entries = readdirSync(dir, { withFileTypes: true });
    } catch {
      return;
    }

    for (const entry of entries) {
      const path = join(dir, entry.name);
      if (!entry.isDirectory()) {
        continue;
      }
      if (shouldPrune(path)) {
        continue;
      }
      if (entry.name === '__pycache__') {
        const rel = relativeTarget(path);
        pycachePaths.push(rel);
        continue;
      }
      walk(path);
    }
  }

  walk(ROOT_DIR);

  for (const entry of readdirSync(ROOT_DIR, { withFileTypes: true })) {
    if (entry.isDirectory() && entry.name.endsWith('.egg-info')) {
      eggInfoPaths.push(entry.name);
    }
  }

  const targets = [];
  if (pycachePaths.length > 0) {
    targets.push(
      uninstallTargetGroup('python-bytecode-caches', 'Python bytecode caches', pycachePaths, 'artifacts'),
    );
  }
  if (eggInfoPaths.length > 0) {
    targets.push(
      uninstallTargetGroup('python-package-metadata', 'Python package metadata directories', eggInfoPaths, 'artifacts'),
    );
  }
  return targets;
}

function uninstallPlan() {
  return [...staticTargets(), ...discoverDynamicTargets()];
}

function safetyNotes() {
  return [
    'app:uninstall defaults to a dry-run plan.',
    'Removing files requires an explicit scope plus --yes.',
    'Only app-owned or generated local artifacts are in scope: build/test caches, dependency directories, repo-local pnpm store, and app-owned helper service state/log directories.',
    'User secrets, provider accounts, brokerage configuration, host-owned services, global tools, Keychain items, and trading proposal approvals are preserved.',
    'Recorded service state files block service-state removal; stop app-owned services first so live processes are not orphaned.',
  ];
}

function selectTargets(plan, selectedScopes) {
  return plan.map((target) => ({
    ...target,
    selected: selectedScopes.has(target.scope),
  }));
}

function targetExists(target) {
  if (Array.isArray(target.paths)) {
    return target.paths.some((path) => existsSync(path));
  }
  return existsSync(target.path);
}

function blockingFile(target) {
  return target.blocking_files.find((file) => existsSync(file.path)) ?? null;
}

function plannedTarget(target, selectedScopes) {
  return {
    ...target,
    exists: targetExists(target),
    status:
      selectedScopes.size === 0 || target.selected
        ? 'planned'
        : 'deferred',
    exit_code: null,
    stdout: '',
    stderr: '',
  };
}

function skippedTarget(target, reason) {
  return {
    ...target,
    exists: targetExists(target),
    status: 'skipped',
    reason,
    exit_code: null,
    stdout: '',
    stderr: '',
  };
}

function blockedTarget(target, blocker) {
  return {
    ...target,
    exists: targetExists(target),
    status: 'blocked',
    reason: `Recorded service state file remains: ${blocker.relative_path}`,
    exit_code: 1,
    stdout: '',
    stderr: '',
  };
}

function removeTarget(target) {
  if (Array.isArray(target.paths)) {
    const removedPaths = [];
    for (const path of target.paths) {
      if (!existsSync(path)) {
        continue;
      }
      const stat = statSync(path);
      rmSync(path, { recursive: stat.isDirectory(), force: true });
      removedPaths.push(relativeTarget(path));
    }
    return {
      ...target,
      exists: removedPaths.length > 0,
      status: removedPaths.length > 0 ? 'removed' : 'missing',
      removed_paths: removedPaths,
      exit_code: 0,
      stdout: '',
      stderr: '',
    };
  }

  if (!targetExists(target)) {
    return {
      ...target,
      exists: false,
      status: 'missing',
      exit_code: 0,
      stdout: '',
      stderr: '',
    };
  }

  const stat = statSync(target.path);
  rmSync(target.path, { recursive: stat.isDirectory(), force: true });
  return {
    ...target,
    exists: true,
    status: 'removed',
    exit_code: 0,
    stdout: '',
    stderr: '',
  };
}

function buildPayload(options) {
  assertSafeRoot(ROOT_DIR);
  const selectedScopes = options.selectedScopes;
  const dryRun = !(options.yes && !options.dryRun);
  const plan = selectTargets(uninstallPlan(), selectedScopes);
  const targets = [];
  let exitCode = 0;
  let mutated = false;
  let previousFailure = false;

  for (const target of plan) {
    if (dryRun || !target.selected) {
      targets.push(plannedTarget(target, selectedScopes));
      continue;
    }
    if (previousFailure) {
      targets.push(skippedTarget(target, 'A previous selected uninstall target failed or was blocked.'));
      continue;
    }

    const blocker = blockingFile(target);
    if (blocker) {
      targets.push(blockedTarget(target, blocker));
      previousFailure = true;
      exitCode = 1;
      continue;
    }

    const result = removeTarget(target);
    targets.push(result);
    mutated = mutated || result.status === 'removed';
  }

  return {
    payload: {
      action: 'uninstall',
      mode: 'scoped',
      root: ROOT_DIR,
      dry_run: dryRun,
      approved: options.yes,
      mutated,
      selected_scopes: SCOPE_IDS.filter((scope) => selectedScopes.has(scope)),
      safety_notes: safetyNotes(),
      targets,
      next_commands: [
        'pnpm run app:uninstall -- --dry-run',
        'pnpm run app:stop -- --all --yes',
        'pnpm run app:uninstall -- --artifacts --deps --service-state --yes',
        'pnpm run app:doctor',
      ],
    },
    exitCode,
  };
}

function renderHuman(payload) {
  process.stdout.write('Agentic Trader app:uninstall\n');
  process.stdout.write(`root: ${payload.root}\n`);
  process.stdout.write(`dry-run: ${payload.dry_run ? 'yes' : 'no'}\n`);
  process.stdout.write(
    `selected: ${
      payload.selected_scopes.length > 0
        ? payload.selected_scopes.join(', ')
        : 'none'
    }\n`,
  );
  for (const target of payload.targets) {
    const marker =
      target.status === 'removed'
        ? 'removed'
        : target.status === 'blocked'
          ? 'blocked'
          : target.status;
    process.stdout.write(`${marker} ${target.id}: ${target.relative_path}\n`);
    if (target.reason) {
      process.stdout.write(`  ${target.reason}\n`);
    }
  }
  if (payload.dry_run) {
    process.stdout.write('Run pnpm run app:uninstall -- --artifacts --deps --yes to remove selected local artifacts/dependencies.\n');
  }
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  const { payload, exitCode } = buildPayload(options);
  if (options.json) {
    process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
  } else {
    renderHuman(payload);
  }
  process.exit(exitCode);
}

main();
