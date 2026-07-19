import { ROOT_DIR } from '../app-lifecycle.mjs';
import { SCOPE_IDS } from './options.mjs';

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

export function updatePlan() {
  return [
    updateStep(
      'root-node-workspace',
      'Update root pnpm workspace dependency resolution',
      ['pnpm', 'update', '--recursive', '--latest'],
      'core',
    ),
    updateStep(
      'root-python-lock',
      'Upgrade uv workspace lock metadata',
      ['uv', 'lock', '--upgrade'],
      'core',
    ),
    updateStep(
      'root-python-sync',
      'Sync root uv workspace Python environment with dev extras',
      ['uv', 'sync', '--locked', '--all-extras', '--group', 'dev'],
      'core',
    ),
    updateStep(
      'research-flow-sync',
      'Sync CrewAI Flow workspace member dependencies',
      ['uv', 'sync', '--locked', '--all-packages', '--all-extras', '--group', 'dev'],
      'sidecar',
    ),
    updateStep(
      'camofox-tool-root',
      'Update optional Camofox helper package dependencies without fetching browser binaries',
      ['scripts/run-camofox-pnpm.sh', 'update'],
      'camofox',
      {
        reason:
          'Browser binary fetch remains explicit through fetch:camofox and is not part of app:update.',
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

export function safetyNotes() {
  return [
    'app:update defaults to a dry-run plan.',
    'Mutating updates require an explicit scope plus --yes.',
    'The update lane uses native dependency owners: pnpm for Node workspaces/tool roots and uv for the Python workspace lock/environment.',
    'No trading daemon, app-owned service start/stop, browser binary fetch, Ollama model pull, provider account, secret, brokerage config, or runtime state deletion is performed.',
  ];
}

export function selectSteps(plan, selectedScopes) {
  return plan.map((step) => ({
    ...step,
    selected: selectedScopes.has(step.scope),
  }));
}

export function nextCommands() {
  return [
    'pnpm run app:update -- --dry-run',
    'pnpm run app:update -- --core --sidecar --build --status --yes',
    'pnpm run app:doctor',
  ];
}

export function selectedScopesList(selectedScopes) {
  return SCOPE_IDS.filter((scope) => selectedScopes.has(scope));
}
