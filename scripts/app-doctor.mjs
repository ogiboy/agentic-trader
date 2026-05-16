#!/usr/bin/env node
import { parseJsonPayload, resolveAgenticTrader, ROOT_DIR, runLifecycleCommand } from './lib/app-lifecycle.mjs';

function usage(exitCode = 0) {
  process.stdout.write(`Usage: node scripts/app-doctor.mjs [options]

Read setup, provider, V1 readiness, and app-owned service status without
installing dependencies, starting/stopping services, pulling models, opening a
browser, or starting a trading daemon.

Options:
  --json      Emit a machine-readable summary.
  -h, --help  Show this help.
`);
  process.exit(exitCode);
}

function parseArgs(argv) {
  const options = { json: false };
  for (const arg of argv) {
    if (arg === '--') {
      continue;
    } else if (arg === '--json') {
      options.json = true;
    } else if (arg === '-h' || arg === '--help') {
      usage(0);
    } else {
      process.stderr.write(`Unknown option: ${arg}\n`);
      usage(2);
    }
  }
  return options;
}

function step(id, label, args) {
  return { id, label, args };
}

function doctorSteps() {
  return [
    step('setup-status', 'Workspace setup and optional tool readiness', ['setup-status', '--json']),
    step('model-service', 'App-owned model-service readiness', ['model-service', 'status', '--json']),
    step('camofox-service', 'App-owned Camofox helper readiness', ['camofox-service', 'status', '--json']),
    step('webgui-service', 'App-owned Web GUI readiness', ['webgui-service', 'status', '--json']),
    step('provider-diagnostics', 'Provider/source ladder diagnostics', ['provider-diagnostics', '--json']),
    step('v1-readiness', 'Network-light V1 paper readiness gates', ['v1-readiness', '--json']),
  ];
}

function runStep(cliPath, stepInfo) {
  const command = [cliPath, ...stepInfo.args];
  const completed = runLifecycleCommand(command);
  return {
    id: stepInfo.id,
    label: stepInfo.label,
    command,
    mutates: false,
    status: completed.status === 0 ? 'passed' : 'failed',
    exit_code: completed.status ?? 1,
    payload: completed.status === 0 ? parseJsonPayload(completed.stdout) : null,
    stdout: completed.stdout,
    stderr: completed.stderr,
  };
}

function safetyNotes() {
  return [
    'app:doctor is read-only and never starts a trading daemon.',
    'Provider checks are network-light; local model generation probes stay explicit through v1-readiness --provider-check or model-service status --probe-generation.',
    'No dependencies, browser binaries, Ollama models, provider accounts, secrets, brokerage config, or app-owned processes are changed.',
  ];
}

function renderHuman(payload) {
  process.stdout.write('Agentic Trader app:doctor\n');
  if (!payload.cli_path) {
    process.stdout.write('agentic-trader entrypoint was not found. Run make setup, then retry app:doctor.\n');
    return;
  }
  for (const result of payload.steps) {
    process.stdout.write(`${result.status === 'passed' ? 'ok' : 'fail'} ${result.id}: ${result.label}\n`);
  }
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  const cliPath = resolveAgenticTrader();
  const steps = cliPath ? doctorSteps().map((stepInfo) => runStep(cliPath, stepInfo)) : [];
  const exitCode = cliPath && steps.every((result) => result.exit_code === 0) ? 0 : 1;
  const payload = {
    action: 'doctor',
    dry_run: false,
    mutated: false,
    cli_path: cliPath,
    safety_notes: safetyNotes(),
    steps,
  };

  if (options.json) {
    process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
  } else {
    renderHuman(payload);
  }
  process.exit(exitCode);
}

main();
