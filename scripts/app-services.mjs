#!/usr/bin/env node
import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT_DIR = join(dirname(fileURLToPath(import.meta.url)), '..');
const SERVICE_IDS = ['model-service', 'camofox-service', 'webgui-service'];

function usage(exitCode = 0) {
  process.stdout.write(`Usage: node scripts/app-services.mjs <start|stop> [options]

Plan or run app-owned service lifecycle slices.

Default behavior is a dry-run plan. Mutating start/stop requires an explicit
service selection plus --yes.

Options:
  --webgui        Select the app-owned Web GUI service.
  --model-service Select the app-owned local model-service.
  --camofox-service Select the app-owned Camofox helper service.
  --all           Select all app-owned helper services.
  --yes           Approve the selected mutating service action.
  --dry-run       Print the service plan without starting or stopping services.
  --json          Emit a machine-readable summary.
  --open-browser  With start + webgui, ask the OS to open the Web GUI URL.
  -h, --help      Show this help.
`);
  process.exit(exitCode);
}

function parseArgs(argv) {
  const [mode, ...rest] = argv.filter((arg) => arg !== '--');
  if (mode === '-h' || mode === '--help') {
    usage(0);
  }
  if (mode !== 'start' && mode !== 'stop') {
    process.stderr.write('Expected lifecycle mode: start or stop.\n');
    usage(2);
  }

  const options = {
    mode,
    dryRun: false,
    json: false,
    openBrowser: false,
    selectedServices: new Set(),
    yes: false,
  };

  for (const arg of rest) {
    if (arg === '--webgui') {
      options.selectedServices.add('webgui-service');
    } else if (arg === '--model-service') {
      options.selectedServices.add('model-service');
    } else if (arg === '--camofox-service') {
      options.selectedServices.add('camofox-service');
    } else if (arg === '--all') {
      for (const serviceId of SERVICE_IDS) {
        options.selectedServices.add(serviceId);
      }
    } else if (arg === '--dry-run') {
      options.dryRun = true;
    } else if (arg === '--json') {
      options.json = true;
    } else if (arg === '--open-browser') {
      options.openBrowser = true;
    } else if (arg === '--yes') {
      options.yes = true;
    } else if (arg === '-h' || arg === '--help') {
      usage(0);
    } else {
      process.stderr.write(`Unknown option: ${arg}\n`);
      usage(2);
    }
  }

  if (options.openBrowser && mode !== 'start') {
    process.stderr.write('--open-browser only applies to app:start.\n');
    usage(2);
  }
  if (options.openBrowser && !options.selectedServices.has('webgui-service')) {
    process.stderr.write('--open-browser requires selecting --webgui or --all.\n');
    usage(2);
  }
  if (options.yes && !options.dryRun && options.selectedServices.size === 0) {
    process.stderr.write('Select at least one service before using --yes.\n');
    usage(2);
  }

  return options;
}

function commandExists(command) {
  const result = spawnSync('sh', ['-c', 'command -v "$1"', 'sh', command], {
    cwd: ROOT_DIR,
    encoding: 'utf8',
  });
  return result.status === 0 ? result.stdout.trim() : null;
}

function resolveAgenticTrader() {
  if (Object.prototype.hasOwnProperty.call(process.env, 'AGENTIC_TRADER_CLI')) {
    return process.env.AGENTIC_TRADER_CLI || null;
  }
  const worktreeEntrypoint = join(ROOT_DIR, '.venv/bin/agentic-trader');
  if (existsSync(worktreeEntrypoint)) {
    return worktreeEntrypoint;
  }
  return commandExists('agentic-trader');
}

function serviceStep(id, label, args, selected, reason) {
  return {
    id,
    label,
    command: ['agentic-trader', ...args],
    category: 'app-owned-service',
    mutates: true,
    selected,
    reason,
  };
}

function startPlan(options) {
  return [
    serviceStep(
      'model-service',
      'Start app-owned loopback Ollama/model-service',
      ['model-service', 'start', '--host', '127.0.0.1', '--json'],
      options.selectedServices.has('model-service'),
      'Select with --model-service or --all after provider ownership is configured.',
    ),
    serviceStep(
      'camofox-service',
      'Start app-owned loopback Camofox helper',
      ['camofox-service', 'start', '--host', '127.0.0.1', '--json'],
      options.selectedServices.has('camofox-service'),
      'Select with --camofox-service or --all after loopback/access-key readiness is configured.',
    ),
    serviceStep(
      'webgui-service',
      'Start app-owned loopback Web GUI service',
      [
        'webgui-service',
        'start',
        options.openBrowser ? '--open-browser' : '--no-open-browser',
        '--json',
      ],
      options.selectedServices.has('webgui-service'),
      'Select with --webgui or --all. Browser opening stays opt-in through --open-browser.',
    ),
  ];
}

function stopPlan(options) {
  return [
    serviceStep(
      'webgui-service',
      'Stop app-owned Web GUI service if recorded by the app',
      ['webgui-service', 'stop', '--json'],
      options.selectedServices.has('webgui-service'),
      'Select with --webgui or --all. Host-owned/external Web GUI listeners are not claimed.',
    ),
    serviceStep(
      'camofox-service',
      'Stop app-owned Camofox helper if recorded by the app',
      ['camofox-service', 'stop', '--json'],
      options.selectedServices.has('camofox-service'),
      'Select with --camofox-service or --all. Host-owned browser helpers are not claimed.',
    ),
    serviceStep(
      'model-service',
      'Stop app-owned model-service if recorded by the app',
      ['model-service', 'stop', '--json'],
      options.selectedServices.has('model-service'),
      'Select with --model-service or --all. Host-owned Ollama on 11434 is preserved.',
    ),
  ];
}

function safetyNotes(mode, options) {
  const verb = mode === 'start' ? 'starts' : 'stops';
  return [
    `app:${mode} defaults to a dry-run plan and only ${verb} explicitly selected app-owned service surfaces after --yes.`,
    'No dependency install, browser binary fetch, Ollama model pull, provider account, secret, brokerage config, or trading daemon is changed.',
    'Service ownership remains delegated to model-service, camofox-service, and webgui-service safeguards; host-owned processes must not be killed or claimed.',
    options.openBrowser
      ? 'Web GUI browser opening was explicitly requested with --open-browser.'
      : 'Web GUI browser opening is disabled by default; pass --open-browser when that is intended.',
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

function blockedStep(step, reason) {
  return {
    ...step,
    status: 'blocked',
    reason,
    exit_code: 1,
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

function parsePayload(stdout) {
  try {
    return JSON.parse(stdout);
  } catch {
    return null;
  }
}

function commandSucceeded(mode, payload) {
  if (!payload || typeof payload !== 'object') {
    return false;
  }
  if (mode === 'start') {
    return payload.app_owned === true;
  }
  return payload.app_owned !== true;
}

function runStep(cliPath, step, mode) {
  const completed = spawnSync(cliPath, step.command.slice(1), {
    cwd: ROOT_DIR,
    env: process.env,
    encoding: 'utf8',
    stdio: 'pipe',
  });
  const payload = completed.status === 0 ? parsePayload(completed.stdout) : null;
  const passed = completed.status === 0 && commandSucceeded(mode, payload);
  return {
    ...step,
    resolved_command: [cliPath, ...step.command.slice(1)],
    status: passed ? 'passed' : 'failed',
    exit_code: completed.status ?? 1,
    payload,
    stdout: completed.stdout,
    stderr: completed.stderr,
  };
}

function buildPayload(options) {
  const dryRun = !(options.yes && !options.dryRun);
  const cliPath = resolveAgenticTrader();
  const plan = options.mode === 'start' ? startPlan(options) : stopPlan(options);
  const selectedServices = SERVICE_IDS.filter((serviceId) => options.selectedServices.has(serviceId));
  const results = [];
  let exitCode = 0;
  let attemptedMutation = false;
  let previousFailure = false;

  for (const step of plan) {
    if (!step.selected || dryRun) {
      results.push(plannedStep(step));
      continue;
    }
    if (!cliPath) {
      results.push(blockedStep(step, 'agentic-trader entrypoint was not found. Run make setup, then retry the lifecycle command.'));
      exitCode = 1;
      continue;
    }
    if (options.mode === 'start' && previousFailure) {
      results.push(skippedStep(step, 'A previous selected start step failed.'));
      continue;
    }

    attemptedMutation = true;
    const result = runStep(cliPath, step, options.mode);
    results.push(result);
    if (result.status !== 'passed') {
      exitCode = 1;
      previousFailure = true;
    }
  }

  return {
    payload: {
      action: options.mode,
      mode: 'services',
      dry_run: dryRun,
      mutated: attemptedMutation,
      approved: options.yes,
      selected_services: selectedServices,
      cli_path: cliPath,
      open_browser: options.openBrowser,
      safety_notes: safetyNotes(options.mode, options),
      steps: results,
      next_commands: [
        'pnpm run app:doctor',
        'pnpm run app:start -- --webgui --yes',
        'pnpm run app:stop -- --all --yes',
      ],
    },
    exitCode,
  };
}

function renderHuman(payload) {
  process.stdout.write(`Agentic Trader app:${payload.action}\n`);
  process.stdout.write(`dry-run: ${payload.dry_run ? 'yes' : 'no'}\n`);
  if (payload.selected_services.length > 0) {
    process.stdout.write(`selected: ${payload.selected_services.join(', ')}\n`);
  } else {
    process.stdout.write('selected: none\n');
  }
  for (const step of payload.steps) {
    const marker = step.status === 'passed' ? 'ok' : step.status === 'failed' ? 'fail' : step.status;
    process.stdout.write(`${marker} ${step.id}: ${step.label}\n`);
    if (step.status === 'deferred' && step.reason) {
      process.stdout.write(`  ${step.reason}\n`);
    }
    if (step.status === 'blocked' && step.reason) {
      process.stdout.write(`  ${step.reason}\n`);
    }
  }
  if (payload.dry_run) {
    process.stdout.write(`Run pnpm run app:${payload.action} -- --webgui --yes to ${payload.action} the Web GUI service only.\n`);
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
