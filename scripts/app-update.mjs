#!/usr/bin/env node
import { spawnSync } from 'node:child_process';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT_DIR = join(dirname(fileURLToPath(import.meta.url)), '..');
const RESEARCH_FLOW_DIR = join(ROOT_DIR, 'sidecars', 'research_flow');

const SCOPE_IDS = ['core', 'sidecar', 'camofox', 'build', 'status'];

function usage(exitCode = 0) {
  process.stdout.write(`Usage: node scripts/app-update.mjs [options]

Plan or run the app update lifecycle lane.

Default behavior is a dry-run plan. Mutating updates require selecting one or
more scopes plus --yes.

Options:
  --core     Update root pnpm workspace and root uv lock/env owners.
  --sidecar  Update the CrewAI Flow sidecar uv lock/env owner.
  --camofox  Update optional Camofox helper package dependencies only.
  --build    Run repository build/check validation after selected updates.
  --status   Run app:doctor after selected updates.
  --all      Select every update, build, and status scope.
  --yes      Approve selected update actions.
  --dry-run  Print the update plan without running commands.
  --json     Emit a machine-readable summary.
  -h, --help Show this help.
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
    } else if (arg === '--core') {
      options.selectedScopes.add('core');
    } else if (arg === '--sidecar') {
      options.selectedScopes.add('sidecar');
    } else if (arg === '--camofox') {
      options.selectedScopes.add('camofox');
    } else if (arg === '--build') {
      options.selectedScopes.add('build');
    } else if (arg === '--status') {
      options.selectedScopes.add('status');
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
    process.stderr.write('Select at least one update scope before using --yes.\n');
    usage(2);
  }

  return options;
}

function updateStep(id, label, command, scope, options = {}) {
  return {
    id,
    label,
    command,
    cwd: options.cwd ?? ROOT_DIR,
    scope,
    mutates: options.mutates ?? true,
    selected: false,
    reason: options.reason,
  };
}

function updatePlan() {
  return [
    updateStep(
      'root-node-workspace',
      'Update root pnpm workspace dependency resolution',
      ['pnpm', 'update', '--recursive', '--latest'],
      'core',
    ),
    updateStep(
      'root-python-lock',
      'Upgrade root uv lock metadata',
      ['uv', 'lock', '--upgrade'],
      'core',
    ),
    updateStep(
      'root-python-sync',
      'Sync root uv Python environment with dev extras',
      ['uv', 'sync', '--locked', '--all-extras', '--group', 'dev'],
      'core',
    ),
    updateStep(
      'research-flow-lock',
      'Upgrade CrewAI Flow sidecar uv lock metadata',
      ['uv', 'lock', '--upgrade'],
      'sidecar',
      { cwd: RESEARCH_FLOW_DIR },
    ),
    updateStep(
      'research-flow-sync',
      'Sync CrewAI Flow sidecar uv environment',
      ['uv', 'sync', '--locked'],
      'sidecar',
      { cwd: RESEARCH_FLOW_DIR },
    ),
    updateStep(
      'camofox-tool-root',
      'Update optional Camofox helper package dependencies without fetching browser binaries',
      ['pnpm', '--dir', 'tools/camofox-browser', '--ignore-workspace', 'update'],
      'camofox',
      {
        reason: 'Browser binary fetch remains explicit through fetch:camofox and is not part of app:update.',
      },
    ),
    updateStep(
      'workspace-check',
      'Run repository static/build/test checks after selected updates',
      ['pnpm', 'run', 'check'],
      'build',
      { mutates: false },
    ),
    updateStep(
      'research-flow-check',
      'Run CrewAI Flow sidecar checks after selected updates',
      ['pnpm', 'run', 'check:research-flow'],
      'build',
      { mutates: false },
    ),
    updateStep(
      'camofox-check',
      'Run optional Camofox helper syntax check after selected updates',
      ['pnpm', 'run', 'check:camofox'],
      'build',
      { mutates: false },
    ),
    updateStep(
      'app-doctor',
      'Report setup, provider, V1, and app-owned service readiness after updates',
      ['pnpm', 'run', 'app:doctor', '--', '--json'],
      'status',
      { mutates: false },
    ),
  ];
}

function safetyNotes() {
  return [
    'app:update defaults to a dry-run plan.',
    'Mutating updates require an explicit scope plus --yes.',
    'The update lane uses native dependency owners: pnpm for Node workspaces/tool roots and uv for Python locks/environments.',
    'No trading daemon, app-owned service start/stop, browser binary fetch, Ollama model pull, provider account, secret, brokerage config, or runtime state deletion is performed.',
  ];
}

function selectSteps(plan, selectedScopes) {
  return plan.map((step) => ({
    ...step,
    selected: selectedScopes.has(step.scope),
  }));
}

function plannedStep(step, selectedScopes) {
  return {
    ...step,
    status:
      selectedScopes.size === 0 || step.selected
        ? 'planned'
        : 'deferred',
    exit_code: null,
    stdout: '',
    stderr: '',
  };
}

function skippedStep(step, reason) {
  return {
    ...step,
    status: 'skipped',
    reason,
    exit_code: null,
    stdout: '',
    stderr: '',
  };
}

function runStep(step) {
  const completed = spawnSync(step.command[0], step.command.slice(1), {
    cwd: step.cwd,
    env: process.env,
    encoding: 'utf8',
    stdio: 'pipe',
  });
  return {
    ...step,
    status: completed.status === 0 ? 'passed' : 'failed',
    exit_code: completed.status ?? 1,
    stdout: completed.stdout,
    stderr: completed.stderr,
  };
}

function buildPayload(options) {
  const selectedScopes = options.selectedScopes;
  const dryRun = !(options.yes && !options.dryRun);
  const plan = selectSteps(updatePlan(), selectedScopes);
  const steps = [];
  let exitCode = 0;
  let mutated = false;
  let previousFailure = false;

  for (const step of plan) {
    if (dryRun || !step.selected) {
      steps.push(plannedStep(step, selectedScopes));
      continue;
    }
    if (previousFailure) {
      steps.push(skippedStep(step, 'A previous selected update step failed.'));
      continue;
    }
    const result = runStep(step);
    steps.push(result);
    mutated = mutated || step.mutates;
    if (result.exit_code !== 0) {
      previousFailure = true;
      exitCode = 1;
    }
  }

  return {
    payload: {
      action: 'update',
      mode: 'scoped',
      dry_run: dryRun,
      approved: options.yes,
      mutated,
      selected_scopes: SCOPE_IDS.filter((scope) => selectedScopes.has(scope)),
      safety_notes: safetyNotes(),
      steps,
      next_commands: [
        'pnpm run app:update -- --dry-run',
        'pnpm run app:update -- --core --sidecar --build --status --yes',
        'pnpm run app:doctor',
      ],
    },
    exitCode,
  };
}

function renderHuman(payload) {
  process.stdout.write('Agentic Trader app:update\n');
  process.stdout.write(`dry-run: ${payload.dry_run ? 'yes' : 'no'}\n`);
  process.stdout.write(
    `selected: ${
      payload.selected_scopes.length > 0
        ? payload.selected_scopes.join(', ')
        : 'none'
    }\n`,
  );
  for (const step of payload.steps) {
    const marker =
      step.status === 'passed'
        ? 'ok'
        : step.status === 'failed'
          ? 'fail'
          : step.status;
    const cwdNote = step.cwd === ROOT_DIR ? '' : ` (${step.cwd})`;
    process.stdout.write(`${marker} ${step.id}${cwdNote}: ${step.label}\n`);
    if (step.reason) {
      process.stdout.write(`  ${step.reason}\n`);
    }
  }
  if (payload.dry_run) {
    process.stdout.write('Run pnpm run app:update -- --core --build --status --yes to execute a scoped update lane.\n');
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
