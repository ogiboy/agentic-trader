#!/usr/bin/env node
import {
  ROOT_DIR,
  parseJsonPayload,
  persistToolOwnership,
  readToolOwnership,
  runLifecycleCommand,
} from './lib/app-lifecycle.mjs';

const SAFE_ALL_SCOPES = ['core', 'sidecar', 'webgui', 'status'];
const SCOPE_IDS = [
  'core',
  'sidecar',
  'camofox-deps',
  'camofox-browser',
  'model-service',
  'camofox-service',
  'webgui',
  'status',
];
const OWNER_MODES = ['undecided', 'host-owned', 'app-owned', 'api-key-only', 'skipped'];

function usage(exitCode = 0) {
  process.stdout.write(`Usage: node scripts/app-up.mjs [options]

Plan or run the guided first-run lifecycle.

Default behavior is a dry-run plan. Executing setup, helper service starts, or
Web GUI launch requires explicit scopes plus --yes.

Options:
  --core              Run root app:setup core repair.
  --sidecar           Install or repair the CrewAI Flow sidecar environment.
  --camofox-deps      Install optional Camofox helper dependencies only.
  --camofox-browser   Fetch/update the optional Camofox browser binary.
  --model-service     Start the app-owned local model-service.
  --camofox-service   Start the app-owned Camofox helper service.
  --webgui            Start the app-owned Web GUI service.
  --status            Run app:doctor after selected setup/start steps.
  --all               Select safe first-run scopes: core, sidecar, webgui,
                      and status. It does not install optional browser helpers,
                      fetch browser binaries, pull models, or start optional
                      model or Camofox services.
  --ollama-owner MODE    MODE is host-owned, app-owned, api-key-only, or skipped.
  --firecrawl-owner MODE MODE is host-owned, app-owned, api-key-only, or skipped.
  --camofox-owner MODE   MODE is host-owned, app-owned, api-key-only, or skipped.
  --open-browser      With --webgui, ask app:start to open the Web GUI browser.
  --yes               Approve selected lifecycle actions.
  --dry-run           Print the guided plan without running commands.
  --json              Emit a machine-readable summary.
  -h, --help          Show this help.
`);
  process.exit(exitCode);
}

function readValue(argv, index, optionName) {
  const arg = argv[index];
  const eq = `${optionName}=`;
  if (arg.startsWith(eq)) {
    return { value: arg.slice(eq.length), nextIndex: index };
  }
  if (arg === optionName) {
    const value = argv[index + 1];
    if (!value || value.startsWith('--')) {
      process.stderr.write(`${optionName} requires an ownership mode.\n`);
      usage(2);
    }
    return { value, nextIndex: index + 1 };
  }
  return null;
}

function parseOwner(value, optionName) {
  if (!OWNER_MODES.includes(value) || value === 'undecided') {
    process.stderr.write(
      `${optionName} must be one of: host-owned, app-owned, api-key-only, skipped.\n`,
    );
    usage(2);
  }
  return value;
}

function parseArgs(argv) {
  const persistedOwnership = readToolOwnership().decisions_by_tool;
  const options = {
    dryRun: false,
    json: false,
    openBrowser: false,
    owners: {
      ollama: persistedOwnership.ollama?.mode ?? 'undecided',
      firecrawl: persistedOwnership.firecrawl?.mode ?? 'undecided',
      camofox: persistedOwnership.camofox?.mode ?? 'undecided',
    },
    ownerOverrides: new Set(),
    selectedScopes: new Set(),
    yes: false,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--') {
      continue;
    }
    const ollamaOwner = readValue(argv, index, '--ollama-owner');
    const firecrawlOwner = readValue(argv, index, '--firecrawl-owner');
    const camofoxOwner = readValue(argv, index, '--camofox-owner');
    if (ollamaOwner) {
      options.owners.ollama = parseOwner(ollamaOwner.value, '--ollama-owner');
      options.ownerOverrides.add('ollama');
      index = ollamaOwner.nextIndex;
    } else if (firecrawlOwner) {
      options.owners.firecrawl = parseOwner(firecrawlOwner.value, '--firecrawl-owner');
      options.ownerOverrides.add('firecrawl');
      index = firecrawlOwner.nextIndex;
    } else if (camofoxOwner) {
      options.owners.camofox = parseOwner(camofoxOwner.value, '--camofox-owner');
      options.ownerOverrides.add('camofox');
      index = camofoxOwner.nextIndex;
    } else if (arg === '--core') {
      options.selectedScopes.add('core');
    } else if (arg === '--sidecar') {
      options.selectedScopes.add('sidecar');
    } else if (arg === '--camofox-deps') {
      options.selectedScopes.add('camofox-deps');
    } else if (arg === '--camofox-browser') {
      options.selectedScopes.add('camofox-browser');
    } else if (arg === '--model-service') {
      options.selectedScopes.add('model-service');
    } else if (arg === '--camofox-service') {
      options.selectedScopes.add('camofox-service');
    } else if (arg === '--webgui') {
      options.selectedScopes.add('webgui');
    } else if (arg === '--status') {
      options.selectedScopes.add('status');
    } else if (arg === '--all') {
      for (const scope of SAFE_ALL_SCOPES) {
        options.selectedScopes.add(scope);
      }
    } else if (arg === '--open-browser') {
      options.openBrowser = true;
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

  if (options.openBrowser && !options.selectedScopes.has('webgui')) {
    process.stderr.write('--open-browser requires selecting --webgui or --all.\n');
    usage(2);
  }
  if (options.yes && !options.dryRun && options.selectedScopes.size === 0) {
    process.stderr.write('Select at least one app:up scope before using --yes.\n');
    usage(2);
  }

  return options;
}

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

function upPlan(options) {
  return [
    upStep(
      'core-setup',
      'Repair root Node workspace and root uv Python environment',
      ['pnpm', 'run', 'app:setup', '--', '--json', '--core', '--yes'],
      'core',
    ),
    upStep(
      'research-flow-sidecar',
      'Install or repair the isolated CrewAI Flow sidecar environment',
      ['pnpm', 'run', 'setup:research-flow'],
      'sidecar',
      {
        reason: 'Sidecar remains isolated under sidecars/research_flow and is not imported by the core runtime.',
      },
    ),
    upStep(
      'camofox-deps',
      'Install optional Camofox helper dependencies without browser download',
      ['pnpm', 'run', 'setup:camofox'],
      'camofox-deps',
      {
        requiresOwner: { tool: 'camofox', mode: 'app-owned' },
        reason: 'Camofox helper dependencies are repo-local app-owned tool infrastructure.',
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
        reason: 'Browser binary fetch can be large and platform-specific, so it requires explicit --camofox-browser.',
      },
    ),
    upStep(
      'model-service-start',
      'Start app-owned loopback Ollama/model-service',
      ['pnpm', 'run', 'app:start', '--', '--json', '--model-service', '--yes'],
      'model-service',
      {
        requiresOwner: { tool: 'ollama', mode: 'app-owned' },
        reason: 'Host-owned or skipped Ollama choices are respected and are never claimed by app:up.',
      },
    ),
    upStep(
      'camofox-service-start',
      'Start app-owned loopback Camofox helper service',
      ['pnpm', 'run', 'app:start', '--', '--json', '--camofox-service', '--yes'],
      'camofox-service',
      {
        requiresOwner: { tool: 'camofox', mode: 'app-owned' },
        reason: 'Camofox service start requires app-owned loopback/access-key readiness.',
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

function safetyNotes() {
  return [
    'app:up defaults to a dry-run plan.',
    'Executing first-run setup requires explicit scopes plus --yes.',
    'The guided flow composes existing lifecycle commands instead of owning a second runtime.',
    'No trading daemon, live broker, provider account, secret, brokerage config, hidden model pull, or hidden browser download is changed.',
    'Camofox browser binary fetch and optional model/Camofox service starts require explicit scopes and app-owned ownership decisions.',
  ];
}

function ownerDecision(tool, mode) {
  const notes = {
    'undecided': 'No ownership choice supplied yet; app:up will defer ownership-sensitive actions.',
    'host-owned': 'Connect/readiness only; app:up must not start, stop, install, or delete this host-owned tool.',
    'app-owned': 'App-owned setup/start may run only for explicitly selected scopes and records owner-only state through existing services.',
    'api-key-only': 'Use ignored environment/keychain authentication only; no CLI install or service ownership is implied.',
    skipped: 'Feature remains degraded/skipped while the paper-first product can still open.',
  };
  return {
    tool,
    mode,
    note: notes[mode],
  };
}

function ownershipDecisions(options) {
  return [
    ownerDecision('ollama', options.owners.ollama),
    ownerDecision('firecrawl', options.owners.firecrawl),
    ownerDecision('camofox', options.owners.camofox),
  ];
}

function ownershipUpdates(options) {
  return Object.fromEntries(
    [...options.ownerOverrides].map((tool) => [tool, options.owners[tool]]),
  );
}

function selectSteps(plan, selectedScopes) {
  return plan.map((step) => ({
    ...step,
    selected: selectedScopes.has(step.scope),
  }));
}

function ownerBlocker(step, owners) {
  if (!step.requires_owner) {
    return null;
  }
  const actual = owners[step.requires_owner.tool];
  if (actual === step.requires_owner.mode) {
    return null;
  }
  if (actual === 'undecided') {
    return `Choose --${step.requires_owner.tool}-owner=${step.requires_owner.mode} before selecting ${step.scope}.`;
  }
  return `${step.scope} requires ${step.requires_owner.tool} ownership ${step.requires_owner.mode}; current choice is ${actual}.`;
}

function plannedStep(step, selectedScopes, owners) {
  const blocker = step.selected ? ownerBlocker(step, owners) : null;
  return {
    ...step,
    status: blocker
      ? 'blocked'
      : selectedScopes.size === 0 || step.selected
        ? 'planned'
        : 'deferred',
    reason: blocker ?? step.reason,
    exit_code: blocker ? 1 : null,
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

function runStep(step) {
  const completed = runLifecycleCommand(step.command, { cwd: step.cwd });
  const payload = completed.status === 0 ? parseJsonPayload(completed.stdout) : null;
  return {
    ...step,
    status: completed.status === 0 ? 'passed' : 'failed',
    exit_code: completed.status ?? 1,
    payload,
    stdout: completed.stdout,
    stderr: completed.stderr,
  };
}

function buildPayload(options) {
  const selectedScopes = options.selectedScopes;
  const dryRun = !(options.yes && !options.dryRun);
  const plan = selectSteps(upPlan(options), selectedScopes);
  const ownershipState = dryRun
    ? { mutated: false, payload: readToolOwnership() }
    : persistToolOwnership(ownershipUpdates(options), 'app-up');
  const steps = [];
  let exitCode = 0;
  let mutated = ownershipState.mutated;
  let previousFailure = false;

  for (const step of plan) {
    if (dryRun || !step.selected) {
      const planned = plannedStep(step, selectedScopes, options.owners);
      steps.push(planned);
      if (!dryRun && step.selected && planned.status === 'blocked') {
        exitCode = 1;
        previousFailure = true;
      }
      continue;
    }

    if (previousFailure) {
      steps.push(skippedStep(step, 'A previous selected app:up step failed or was blocked.'));
      continue;
    }

    const blocker = ownerBlocker(step, options.owners);
    if (blocker) {
      steps.push(blockedStep(step, blocker));
      previousFailure = true;
      exitCode = 1;
      continue;
    }

    const result = runStep(step);
    steps.push(result);
    mutated = mutated || (step.mutates && result.exit_code === 0);
    if (result.exit_code !== 0) {
      previousFailure = true;
      exitCode = 1;
    }
  }

  return {
    payload: {
      action: 'up',
      mode: 'guided-first-run',
      dry_run: dryRun,
      approved: options.yes,
      mutated,
      selected_scopes: SCOPE_IDS.filter((scope) => selectedScopes.has(scope)),
      ownership_decisions: ownershipDecisions(options),
      tool_ownership: ownershipState.payload,
      open_browser: options.openBrowser,
      safety_notes: safetyNotes(),
      steps,
      next_commands: [
        'pnpm run app:up -- --dry-run',
        'pnpm run app:up -- --all --yes',
        'pnpm run app:up -- --model-service --ollama-owner=app-owned --yes',
        'pnpm run app:doctor',
      ],
    },
    exitCode,
  };
}

function renderHuman(payload) {
  process.stdout.write('Agentic Trader app:up\n');
  process.stdout.write(`dry-run: ${payload.dry_run ? 'yes' : 'no'}\n`);
  process.stdout.write(
    `selected: ${
      payload.selected_scopes.length > 0
        ? payload.selected_scopes.join(', ')
        : 'none'
    }\n`,
  );
  process.stdout.write(
    `ownership: ${payload.ownership_decisions
      .map((decision) => `${decision.tool}=${decision.mode}`)
      .join(', ')}\n`,
  );
  for (const step of payload.steps) {
    const marker =
      step.status === 'passed'
        ? 'ok'
        : step.status === 'failed'
          ? 'fail'
          : step.status;
    process.stdout.write(`${marker} ${step.id}: ${step.label}\n`);
    if (step.reason) {
      process.stdout.write(`  ${step.reason}\n`);
    }
  }
  if (payload.dry_run) {
    process.stdout.write('Run pnpm run app:up -- --all --yes for the safe first-run setup path.\n');
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
