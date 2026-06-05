import { ROOT_DIR } from '../app-lifecycle.mjs';
import { SCOPE_IDS } from './options.mjs';

function upStep(id, label, command, scope, options = {}) {
  return {
    id,
    label,
    command,
    cwd: options.cwd ?? ROOT_DIR,
    scope,
    mutates: options.mutates ?? true,
    selected: false,
    reason: options.reason,
    requires_owner: options.requiresOwner,
    large_download: options.largeDownload ?? false,
  };
}

export function upPlan(options) {
  return [
    upStep(
      'core-setup',
      'Repair root Node workspace and root uv Python environment',
      ['pnpm', 'run', 'app:setup', '--', '--json', '--core', '--yes'],
      'core',
    ),
    upStep(
      'research-flow-sidecar',
      'Install or repair the CrewAI Flow workspace member dependencies',
      ['pnpm', 'run', 'setup:research-flow'],
      'sidecar',
      {
        reason:
          'Sidecar remains a subprocess-only workspace member and is not imported by the core runtime.',
      },
    ),
    upStep(
      'camofox-deps',
      'Install optional Camofox helper dependencies without browser download',
      ['pnpm', 'run', 'setup:camofox'],
      'camofox-deps',
      {
        requiresOwner: { tool: 'camofox', mode: 'app-owned' },
        reason:
          'Camofox helper dependencies are repo-local app-owned tool infrastructure.',
      },
    ),
    upStep(
      'camofox-browser',
      'Fetch or update the optional Camofox browser binary',
      ['pnpm', 'run', 'fetch:camofox'],
      'camofox-browser',
      {
        requiresOwner: { tool: 'camofox', mode: 'app-owned' },
        largeDownload: true,
        reason:
          'Browser binary fetch can be large and platform-specific, so it requires explicit --camofox-browser.',
      },
    ),
    upStep(
      'model-service-start',
      'Start app-owned loopback Ollama/model-service',
      ['pnpm', 'run', 'app:start', '--', '--json', '--model-service', '--yes'],
      'model-service',
      {
        requiresOwner: { tool: 'ollama', mode: 'app-owned' },
        reason:
          'Host-owned or skipped Ollama choices are respected and are never claimed by app:up.',
      },
    ),
    upStep(
      'camofox-service-start',
      'Start app-owned loopback Camofox helper service',
      [
        'pnpm',
        'run',
        'app:start',
        '--',
        '--json',
        '--camofox-service',
        '--yes',
      ],
      'camofox-service',
      {
        requiresOwner: { tool: 'camofox', mode: 'app-owned' },
        reason:
          'Camofox service start requires app-owned loopback/access-key readiness.',
      },
    ),
    upStep(
      'webgui-start',
      'Start app-owned loopback Web GUI service',
      [
        'pnpm',
        'run',
        'app:start',
        '--',
        '--json',
        '--webgui',
        options.openBrowser ? '--open-browser' : null,
        '--yes',
      ].filter(Boolean),
      'webgui',
      {
        reason: options.openBrowser
          ? 'Browser opening was explicitly requested.'
          : 'Browser opening stays opt-in; pass --open-browser when intended.',
      },
    ),
    upStep(
      'final-doctor',
      'Report setup, provider, V1, and app-owned service readiness',
      ['pnpm', 'run', 'app:doctor', '--', '--json'],
      'status',
      { mutates: false },
    ),
  ];
}

export function safetyNotes() {
  return [
    'app:up defaults to a dry-run plan.',
    'Executing first-run setup requires explicit scopes plus --yes.',
    'The guided flow composes existing lifecycle commands instead of owning a second runtime.',
    'No trading daemon, live broker, provider account, secret, brokerage config, hidden model pull, or hidden browser download is changed.',
    'Camofox browser binary fetch and optional model/Camofox service starts require explicit scopes and app-owned ownership decisions.',
  ];
}

export function selectSteps(plan, selectedScopes) {
  return plan.map((step) => ({
    ...step,
    selected: selectedScopes.has(step.scope),
  }));
}

export function selectedScopesList(selectedScopes) {
  return SCOPE_IDS.filter((scope) => selectedScopes.has(scope));
}

export function nextCommands() {
  return [
    'pnpm run app:up -- --dry-run',
    'pnpm run app:up -- --all --yes',
    'pnpm run app:up -- --model-service --ollama-owner=app-owned --yes',
    'pnpm run app:doctor',
  ];
}
