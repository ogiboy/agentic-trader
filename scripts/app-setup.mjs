#!/usr/bin/env node
import { spawnSync } from 'node:child_process';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT_DIR = join(dirname(fileURLToPath(import.meta.url)), '..');

function usage(exitCode = 0) {
  process.stdout.write(`Usage: node scripts/app-setup.mjs [options]

Plan or run the conservative setup lifecycle slice.

Default behavior is a dry-run plan. The only mutating path implemented in this
slice is explicit core dependency repair with --core --yes.

Options:
  --core      Select root Node workspace and root uv Python repair.
  --yes       Approve the selected mutating setup scope.
  --dry-run   Print the setup plan without running mutating commands.
  --json      Emit a machine-readable summary.
  -h, --help  Show this help.
`);
  process.exit(exitCode);
}

function parseArgs(argv) {
  const options = {
    core: false,
    dryRun: false,
    json: false,
    yes: false,
  };
  for (const arg of argv) {
    if (arg === '--') {
      continue;
    } else if (arg === '--core') {
      options.core = true;
    } else if (arg === '--dry-run') {
      options.dryRun = true;
    } else if (arg === '--json') {
      options.json = true;
    } else if (arg === '--yes') {
      options.yes = true;
    } else if (arg === '-h' || arg === '--help') {
      usage(0);
    } else {
      process.stderr.write(`Unknown option: ${arg}\n`);
      usage(2);
    }
  }
  if (options.yes && !options.core && !options.dryRun) {
    process.stderr.write('The current app:setup slice requires --core before --yes can mutate setup.\n');
    usage(2);
  }
  return options;
}

function coreStep(id, label, command) {
  return {
    id,
    label,
    command,
    category: 'core',
    mutates: true,
    selected: true,
  };
}

function deferredStep(id, label, command, reason) {
  return {
    id,
    label,
    command,
    category: 'deferred',
    mutates: false,
    selected: false,
    reason,
  };
}

function setupPlan() {
  return [
    coreStep('node-workspace', 'Install and verify root/webgui/docs/tui Node workspace dependencies', [
      'pnpm',
      'run',
      'setup:node',
    ]),
    coreStep('python-env', 'Sync the root uv Python 3.13 development environment', [
      'pnpm',
      'run',
      'install:python',
    ]),
    deferredStep('research-flow-sidecar', 'CrewAI Flow sidecar dependency setup', ['pnpm', 'run', 'setup:research-flow'], 'Sidecar setup stays explicit until app:setup grows opt-in side-application ownership.'),
    deferredStep('camofox-deps', 'Camofox helper dependency setup', ['pnpm', 'run', 'setup:camofox'], 'Browser helper setup remains optional and separate from core dependency repair.'),
    deferredStep('camofox-browser', 'Camofox browser binary fetch', ['pnpm', 'run', 'fetch:camofox'], 'Browser downloads require explicit operator approval and are never hidden in app:setup core repair.'),
    deferredStep('model-service-start', 'App-owned Ollama/model-service start', ['agentic-trader', 'model-service', 'start'], 'Provider ownership and model choice must be explicit before starting or pulling models.'),
    deferredStep('camofox-service-start', 'App-owned Camofox service start', ['agentic-trader', 'camofox-service', 'start'], 'Browser-backed helpers require loopback/access-key readiness before service start.'),
    deferredStep('webgui-service-start', 'App-owned Web GUI service start', ['agentic-trader', 'webgui-service', 'start'], 'Web GUI launch belongs to app:up/app:start, not setup repair.'),
  ];
}

function safetyNotes() {
  return [
    'app:setup defaults to a dry-run plan.',
    'The current mutating scope is only --core --yes: root pnpm workspace setup plus root uv Python sync.',
    'No trading daemon, Web GUI service, model-service, Camofox service, browser binary fetch, Ollama model pull, provider account, secret, or brokerage config is changed.',
    'Optional tools remain deferred until ownership is explicit: host-owned, app-owned, API/key-only, or skipped.',
  ];
}

function plannedStep(step) {
  return {
    ...step,
    status: step.selected ? 'planned' : 'deferred',
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
    cwd: ROOT_DIR,
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
  const requestedMutation = options.core && options.yes && !options.dryRun;
  const dryRun = !requestedMutation;
  const plan = setupPlan();
  const results = [];
  let exitCode = 0;
  let attemptedMutation = false;
  let previousFailure = false;

  for (const step of plan) {
    if (!step.selected) {
      results.push(plannedStep(step));
      continue;
    }
    if (dryRun) {
      results.push(plannedStep(step));
      continue;
    }
    if (previousFailure) {
      results.push(skippedStep(step, 'A previous core setup step failed.'));
      continue;
    }
    attemptedMutation = true;
    const result = runStep(step);
    results.push(result);
    if (result.exit_code !== 0) {
      previousFailure = true;
      exitCode = 1;
    }
  }

  return {
    payload: {
      action: 'setup',
      mode: options.core ? 'core' : 'plan',
      dry_run: dryRun,
      mutated: attemptedMutation,
      approved: options.yes,
      safety_notes: safetyNotes(),
      steps: results,
      next_commands: [
        'pnpm run app:doctor',
        'pnpm run app:setup -- --core --yes',
        'pnpm run app:up (future guided first-run path)',
      ],
    },
    exitCode,
  };
}

function renderHuman(payload) {
  process.stdout.write('Agentic Trader app:setup\n');
  process.stdout.write(`mode: ${payload.mode}\n`);
  process.stdout.write(`dry-run: ${payload.dry_run ? 'yes' : 'no'}\n`);
  for (const step of payload.steps) {
    const marker = step.status === 'passed' ? 'ok' : step.status === 'failed' ? 'fail' : step.status;
    process.stdout.write(`${marker} ${step.id}: ${step.label}\n`);
    if (step.reason) {
      process.stdout.write(`  ${step.reason}\n`);
    }
  }
  if (payload.dry_run) {
    process.stdout.write('Run pnpm run app:setup -- --core --yes to execute only core dependency repair.\n');
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
