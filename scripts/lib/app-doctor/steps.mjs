import { parseJsonPayload, runLifecycleCommand } from '../app-lifecycle.mjs';

function step(id, label, args) {
  return { id, label, args };
}

export function doctorSteps() {
  return [
    step('setup-status', 'Workspace setup and optional tool readiness', [
      'setup-status',
      '--json',
    ]),
    step('model-service', 'App-owned model-service readiness', [
      'model-service',
      'status',
      '--json',
    ]),
    step('camofox-service', 'App-owned Camofox helper readiness', [
      'camofox-service',
      'status',
      '--json',
    ]),
    step('webgui-service', 'App-owned Web GUI readiness', [
      'webgui-service',
      'status',
      '--json',
    ]),
    step('provider-diagnostics', 'Provider/source ladder diagnostics', [
      'provider-diagnostics',
      '--json',
    ]),
    step('v1-readiness', 'Network-light V1 paper readiness gates', [
      'v1-readiness',
      '--json',
    ]),
  ];
}

export function runStep(cliPath, stepInfo) {
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

export function safetyNotes() {
  return [
    'app:doctor is read-only and never starts a trading daemon.',
    'Provider checks are network-light; local model generation probes stay explicit through v1-readiness --provider-check or model-service status --probe-generation.',
    'No dependencies, browser binaries, Ollama models, provider accounts, secrets, brokerage config, or app-owned processes are changed.',
  ];
}
