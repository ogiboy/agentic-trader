#!/usr/bin/env node
import { existsSync, readdirSync, rmSync, statSync } from 'node:fs';
import { dirname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const DEFAULT_ROOT_DIR = join(dirname(fileURLToPath(import.meta.url)), '..');
const ROOT_DIR = resolve(process.env.AGENTIC_TRADER_APP_UNINSTALL_ROOT ?? DEFAULT_ROOT_DIR);
const SCOPE_IDS = ['artifacts', 'deps', 'service-state'];

/**
 * Print CLI usage/help text for the uninstall script and exit the process.
 *
 * Writes a human-readable description of available options and behavior, then terminates the process with the given exit code.
 * @param {number} exitCode - Process exit code to use when terminating (defaults to 0).
 */
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

/**
 * Parse command-line arguments into uninstall options and selected scopes.
 *
 * @param {string[]} argv - CLI arguments to parse (typically `process.argv.slice(2)`).
 * @returns {{dryRun: boolean, json: boolean, selectedScopes: Set<string>, yes: boolean}} An options object:
 *   - `dryRun`: true when the action should be simulated without mutating files.
 *   - `json`: true when output should be emitted as JSON.
 *   - `selectedScopes`: a Set of selected scope IDs (members of `SCOPE_IDS`, e.g. `'artifacts'`, `'deps'`, `'service-state'`).
 *   - `yes`: true when the user approved destructive actions (requires at least one selected scope unless in dry-run).
 */
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

/**
 * Checks whether a directory appears to be an Agentic Trader repository.
 * @param {string} rootDir - Path to the directory to inspect.
 * @returns {boolean} `true` if both `package.json` and `pyproject.toml` exist in `rootDir`, `false` otherwise.
 */
function rootLooksLikeAgenticTrader(rootDir) {
  return existsSync(join(rootDir, 'package.json')) && existsSync(join(rootDir, 'pyproject.toml'));
}

/**
 * Validate that the given directory is an Agentic Trader app root.
 *
 * If `package.json` and `pyproject.toml` are not both present under `rootDir`,
 * writes a refusal message to stderr and exits the process with code `2`.
 * @param {string} rootDir - Path to the directory to validate.
 */
function assertSafeRoot(rootDir) {
  if (!rootLooksLikeAgenticTrader(rootDir)) {
    process.stderr.write(
      `Refusing to uninstall from ${rootDir}: expected package.json and pyproject.toml markers.\n`,
    );
    process.exit(2);
  }
}

/**
 * Compute a path relative to the repository root, returning '.' for the root itself.
 * @param {string} path - The path to resolve against ROOT_DIR.
 * @returns {string} The relative path from ROOT_DIR to `path`, or '.' when `path` equals ROOT_DIR.
 */
function relativeTarget(path) {
  const rel = relative(ROOT_DIR, path);
  return rel === '' ? '.' : rel;
}

/**
 * Resolve a path relative to the application's root and ensure the result is inside that root.
 * @param {string} relativePath - Path resolved against the app root (e.g., '.', 'dist', 'sub/dir').
 * @returns {string} The absolute path inside the application root.
 * @throws {Error} If the resolved path is outside the application root.
 */
function targetPath(relativePath) {
  const resolvedPath = resolve(ROOT_DIR, relativePath);
  const rootWithSep = ROOT_DIR.endsWith(sep) ? ROOT_DIR : `${ROOT_DIR}${sep}`;
  if (resolvedPath !== ROOT_DIR && !resolvedPath.startsWith(rootWithSep)) {
    throw new Error(`Refusing to target path outside app root: ${relativePath}`);
  }
  return resolvedPath;
}

/**
 * Create a single uninstall target object for a specific repository path.
 *
 * @param {string} id - Unique identifier for the target.
 * @param {string} label - Human-readable label describing the target.
 * @param {string} relativePath - Path relative to the repository root that the target represents.
 * @param {string} scope - One of the defined uninstall scopes (e.g., "artifacts", "deps", "service-state").
 * @param {Object} [options] - Additional options.
 * @param {string} [options.reason] - Optional explanatory reason describing why the target exists or should be removed.
 * @param {string[]} [options.blockingFiles] - Paths (relative to the repo root) that, if present, block removal; each will be expanded into `{ path, relative_path }`.
 * @returns {Object} An uninstall target object containing:
 *  - `id`, `label`, `scope`
 *  - `path` (absolute), `relative_path` (relative to the root)
 *  - `mutates: true`, `selected: false`
 *  - optional `reason`
 *  - `blocking_files`: array of `{ path, relative_path }` entries for each provided blocking file
 */
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

/**
 * Create an uninstall target that groups multiple discovered paths for the same logical item.
 *
 * @param {string} id - Unique identifier for the target.
 * @param {string} label - Human-readable label describing the grouped item (e.g., "Python bytecode caches").
 * @param {string[]} relativePaths - Array of paths relative to the repository root; each will be resolved to an absolute path.
 * @param {string} scope - One of the uninstall scope IDs (e.g., "artifacts", "deps", "service-state").
 * @returns {Object} An uninstall target object for a multi-path group. The object has `path: null`, a `paths` array of absolute paths, `relative_path` summarizing the group as "`N discovered <label>`", `relative_paths` for presentation, and metadata (`scope`, `mutates: true`, `selected: false`, `blocking_files: []`).
 */
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

/**
 * Produce the fixed set of common uninstall targets for the repository.
 *
 * Each entry represents a filesystem path (or group of paths) and associated
 * metadata categorized into the `artifacts`, `deps`, or `service-state` scopes.
 * Service-state targets may include `blockingFiles` and a `reason` explaining
 * prerequisites that must be addressed before deletion.
 *
 * @returns {Array<object>} An array of uninstall target objects describing
 *   static paths and metadata used to build the uninstall plan.
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

/**
 * Determines whether a path should be skipped during recursive traversal.
 * @param {string} path - Filesystem path to evaluate (converted to a path relative to the repository root).
 * @returns {boolean} `true` if the path matches a known pruned directory (for example `.git`, `node_modules`, virtualenvs, build/output directories, or other repository-specific vendored/output folders), `false` otherwise.
 */
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

/**
 * Discover Python-related uninstall targets under the repository root and produce corresponding uninstall target groups.
 *
 * Searches the repository tree under ROOT_DIR for directories named `__pycache__` and top-level directories ending with `.egg-info`,
 * and returns uninstall group targets representing Python bytecode caches and package metadata directories (assigned to the `artifacts` scope) when found.
 *
 * @returns {Array<Object>} An array of uninstall target group objects for discovered Python bytecode caches and Python package metadata directories; returns an empty array if none are found.
 */
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

/**
 * Builds the complete uninstall plan for the repository.
 *
 * Combines the fixed set of static uninstall targets with any targets discovered
 * dynamically by scanning the repository (e.g., __pycache__ and *.egg-info).
 *
 * @returns {Array<Object>} An array of uninstall target objects describing all planned targets.
 */
function uninstallPlan() {
  return [...staticTargets(), ...discoverDynamicTargets()];
}

/**
 * Provides human-facing safety notes describing defaults, required approvals, what is in-scope and preserved, and service-state blocking behavior.
 * @returns {string[]} An array of safety note strings used in uninstall reports.
 */
function safetyNotes() {
  return [
    'app:uninstall defaults to a dry-run plan.',
    'Removing files requires an explicit scope plus --yes.',
    'Only app-owned or generated local artifacts are in scope: build/test caches, dependency directories, repo-local pnpm store, and app-owned helper service state/log directories.',
    'User secrets, provider accounts, brokerage configuration, host-owned services, global tools, Keychain items, and trading proposal approvals are preserved.',
    'Recorded service state files block service-state removal; stop app-owned services first so live processes are not orphaned.',
  ];
}

/**
 * Mark each uninstall target in a plan as selected when its scope is included in the provided scopes.
 * @param {Array<Object>} plan - Array of uninstall target objects.
 * @param {Set<string>} selectedScopes - Set of scope IDs that should be selected.
 * @returns {Array<Object>} A new array of targets where each target has a `selected` boolean: `true` if the target's `scope` is in `selectedScopes`, `false` otherwise.
 */
function selectTargets(plan, selectedScopes) {
  return plan.map((target) => ({
    ...target,
    selected: selectedScopes.has(target.scope),
  }));
}

/**
 * Checks whether the uninstall target exists on disk.
 *
 * @param {Object} target - Uninstall target object; either a single-target with `path` or a group-target with `paths`.
 * @returns {boolean} `true` if the target exists (for a group target: at least one path exists), `false` otherwise.
 */
function targetExists(target) {
  if (Array.isArray(target.paths)) {
    return target.paths.some((path) => existsSync(path));
  }
  return existsSync(target.path);
}

/**
 * Find the first blocking file for a target that currently exists on disk.
 * @param {{ blocking_files: Array<{ path: string, relative_path?: string }> }} target - Uninstall target containing a list of blocking files.
 * @returns {{ path: string, relative_path?: string } | null} The first blocking file object whose `path` exists, or `null` if none exist.
 */
function blockingFile(target) {
  return target.blocking_files.find((file) => existsSync(file.path)) ?? null;
}

/**
 * Create a planned status entry for an uninstall target.
 * @param {object} target - The uninstall target object to annotate; may be a single-path or group target and may include a `selected` flag.
 * @param {Set<string>} selectedScopes - The set of scopes chosen by the user.
 * @returns {object} The target augmented with `exists`, `status`, `exit_code`, `stdout`, and `stderr`. `status` is `"planned"` when no scopes are selected or when `target.selected` is truthy, otherwise `"deferred"`.
 */
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

/**
 * Mark a planned uninstall target as skipped and annotate it with existence and status metadata.
 * @param {object} target - The uninstall target object to copy and annotate.
 * @param {string} reason - Human-readable explanation of why the target was skipped.
 * @returns {object} The annotated target with `status: 'skipped'`, `exists` (boolean), `reason`, `exit_code: null`, and empty `stdout`/`stderr`.
 */
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

/**
 * Mark a target as blocked because a recorded service-state file exists.
 *
 * @param {Object} target - The uninstall target object to annotate; its original properties are preserved.
 * @param {Object} blocker - The blocking file descriptor with at least a `relative_path` property.
 * @returns {Object} The input target object extended with `exists` (boolean), `status: 'blocked'`, `reason` explaining the blocker, `exit_code: 1`, and empty `stdout`/`stderr`.
 */
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

/**
 * Remove the filesystem entries described by a single uninstall target or a target group.
 *
 * For a group target (contains `paths`), attempts to remove each existing path and reports which were removed.
 * For a single-path target, removes the target path if it exists.
 *
 * @param {object} target - Uninstall target object; either a group with a `paths` array or a single target with `path`.
 * @returns {object} A copy of the input target augmented with:
 *  - `exists` (boolean): whether any targeted path existed prior to removal,
 *  - `status` (string): `'removed'` if one or more paths were removed, otherwise `'missing'`,
 *  - `removed_paths` (string[]|undefined): for group targets, the list of relative paths that were removed,
 *  - `exit_code` (number): zero on success,
 *  - `stdout` (string) and `stderr` (string): empty strings (placeholders for command output).
 */
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

/**
 * Construct an uninstall payload and compute an exit code by planning and (optionally) executing selected uninstall targets under the repository root.
 *
 * The function validates the repository root, determines whether actions should actually mutate the filesystem (based on `options.yes` and `options.dryRun`), selects targets by scope, and then for each target either records a planned entry, skips it due to a prior failure, marks it blocked if a service-state blocker file exists, or removes it and records the result. If any selected service-state target is blocked, the returned `exitCode` is `1`.
 *
 * @param {Object} options - Execution options controlling selection and approval.
 * @param {Set<string>} options.selectedScopes - Set of scope IDs chosen for execution (elements from SCOPE_IDS).
 * @param {boolean} options.yes - Whether the user approved destructive actions (corresponds to `--yes`).
 * @param {boolean} options.dryRun - Whether to request a dry-run (corresponds to `--dry-run`); combined with `yes` to determine actual mutation.
 * @returns {{ payload: Object, exitCode: number }} An object containing:
 *  - `payload`: the uninstall payload object with metadata (`action`, `mode`, `root`, `dry_run`, `approved`), flags (`mutated`), `selected_scopes`, `safety_notes`, an array of per-target `targets` describing planned/skipped/blocked/removed statuses, and `next_commands` suggestions;
 *  - `exitCode`: `0` on success (no blocked selected service-state targets), `1` if any selected service-state target was blocked.
 */
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

/**
 * Print a concise, human-readable uninstall report to stdout.
 *
 * @param {object} payload - Uninstall payload describing the planned or executed actions.
 * @param {string} payload.root - Resolved repository root path shown in the header.
 * @param {boolean} payload.dry_run - If true, the report indicates dry-run mode and prints the follow-up command.
 * @param {string[]} payload.selected_scopes - Selected uninstall scopes shown in the header (empty means "none").
 * @param {Array<Object>} payload.targets - Ordered list of target status entries to report.
 * @param {string} payload.targets[].id - Target identifier.
 * @param {string} payload.targets[].relative_path - Human-friendly relative path or description for the target.
 * @param {string} payload.targets[].status - Target status string (e.g., "removed", "blocked", "planned", "skipped", "missing").
 * @param {string} [payload.targets[].reason] - Optional explanatory reason printed under the target when present.
 */
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

/**
 * Parse CLI arguments, build the uninstall payload, render output (JSON or human-readable), and exit with the computed code.
 *
 * This function is the CLI entry point: it reads process.argv, constructs the uninstall plan and results via buildPayload,
 * writes either a JSON payload to stdout when `--json` is set or a human-friendly report otherwise, and terminates the process
 * with the payload's exit code.
 */
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
