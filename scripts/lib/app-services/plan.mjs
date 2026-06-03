import { ownershipModeFor } from '../app-lifecycle.mjs';
import { SERVICE_IDS } from './options.mjs';

function serviceStep(id, label, args, selected, reason, options = {}) {
  return {
    id,
    label,
    command: ['agentic-trader', ...args],
    category: 'app-owned-service',
    mutates: true,
    selected,
    reason,
    requires_owner: options.requiresOwner,
  };
}

export function startPlan(options) {
  return [
    serviceStep(
      'model-service',
      'Start app-owned loopback Ollama/model-service',
      ['model-service', 'start', '--host', '127.0.0.1', '--json'],
      options.selectedServices.has('model-service'),
      'Select with --model-service or --all after provider ownership is configured.',
      { requiresOwner: { tool: 'ollama', mode: 'app-owned' } },
    ),
    serviceStep(
      'camofox-service',
      'Start app-owned loopback Camofox helper',
      ['camofox-service', 'start', '--host', '127.0.0.1', '--json'],
      options.selectedServices.has('camofox-service'),
      'Select with --camofox-service or --all after loopback/access-key readiness is configured.',
      { requiresOwner: { tool: 'camofox', mode: 'app-owned' } },
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

export function stopPlan(options) {
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

export function safetyNotes(mode, options) {
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

function serviceFlag(serviceId) {
  if (serviceId === 'webgui-service') {
    return '--webgui';
  }
  if (serviceId === 'model-service') {
    return '--model-service';
  }
  if (serviceId === 'camofox-service') {
    return '--camofox-service';
  }
  return null;
}

function selectedServiceFlags(selectedServices) {
  if (selectedServices.length === SERVICE_IDS.length) {
    return ['--all'];
  }
  return selectedServices.map(serviceFlag).filter((flag) => flag !== null);
}

function defaultServiceFlags(mode) {
  return mode === 'start' ? ['--webgui'] : ['--all'];
}

function serviceMutationCommand(options, selectedServices) {
  const flags = selectedServices.length
    ? selectedServiceFlags(selectedServices)
    : defaultServiceFlags(options.mode);
  const args = ['pnpm', 'run', `app:${options.mode}`, '--', ...flags, '--yes'];
  if (
    options.mode === 'start' &&
    options.openBrowser &&
    flags.includes('--webgui')
  ) {
    args.splice(args.length - 1, 0, '--open-browser');
  }
  return args.join(' ');
}

export function nextCommands(options, selectedServices) {
  return [
    'pnpm run app:doctor',
    serviceMutationCommand(options, selectedServices),
    'pnpm run app:stop -- --all --yes',
  ];
}

export function ownerBlocker(step, mode) {
  if (mode !== 'start' || !step.requires_owner) {
    return null;
  }
  const actual = ownershipModeFor(step.requires_owner.tool);
  if (actual === step.requires_owner.mode) {
    return null;
  }
  if (actual === 'undecided') {
    return `Record ${step.requires_owner.tool} ownership ${step.requires_owner.mode} before starting ${step.id}. Run pnpm run app:up -- --${step.requires_owner.tool}-owner=${step.requires_owner.mode} --${step.id === 'model-service' ? 'model-service' : 'camofox-service'} --yes.`;
  }
  return `${step.id} requires ${step.requires_owner.tool} ownership ${step.requires_owner.mode}; current choice is ${actual}.`;
}
