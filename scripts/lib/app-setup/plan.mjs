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

export function setupPlan() {
  return [
    coreStep(
      'node-workspace',
      'Install and verify root/webgui/docs/tui Node workspace dependencies',
      ['pnpm', 'run', 'setup:node'],
    ),
    coreStep(
      'python-env',
      'Sync the root uv Python 3.13 development environment',
      ['pnpm', 'run', 'install:python'],
    ),
    deferredStep(
      'research-flow-sidecar',
      'CrewAI Flow sidecar dependency setup',
      ['pnpm', 'run', 'setup:research-flow'],
      'Sidecar setup stays explicit until app:setup grows opt-in side-application ownership.',
    ),
    deferredStep(
      'camofox-deps',
      'Camofox helper dependency setup',
      ['pnpm', 'run', 'setup:camofox'],
      'Browser helper setup remains optional and separate from core dependency repair.',
    ),
    deferredStep(
      'camofox-browser',
      'Camofox browser binary fetch',
      ['pnpm', 'run', 'fetch:camofox'],
      'Browser downloads require explicit operator approval and are never hidden in app:setup core repair.',
    ),
    deferredStep(
      'model-service-start',
      'App-owned Ollama/model-service start',
      ['agentic-trader', 'model-service', 'start'],
      'Provider ownership and model choice must be explicit before starting or pulling models.',
    ),
    deferredStep(
      'camofox-service-start',
      'App-owned Camofox service start',
      ['agentic-trader', 'camofox-service', 'start'],
      'Browser-backed helpers require loopback/access-key readiness before service start.',
    ),
    deferredStep(
      'webgui-service-start',
      'App-owned Web GUI service start',
      ['agentic-trader', 'webgui-service', 'start'],
      'Web GUI launch belongs to app:up/app:start, not setup repair.',
    ),
  ];
}

export function safetyNotes() {
  return [
    'app:setup defaults to a dry-run plan.',
    'The current mutating scope is only --core --yes: root pnpm workspace setup plus root uv Python sync.',
    'No trading daemon, Web GUI service, model-service, Camofox service, browser binary fetch, Ollama model pull, provider account, secret, or brokerage config is changed.',
    'Optional tools remain deferred until ownership is explicit: host-owned, app-owned, API/key-only, or skipped.',
  ];
}

export function nextCommands() {
  return [
    'pnpm run app:doctor',
    'pnpm run app:setup -- --core --yes',
    'pnpm run app:up (future guided first-run path)',
  ];
}
