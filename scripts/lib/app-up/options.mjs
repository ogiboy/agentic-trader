import { readToolOwnership } from '../app-lifecycle.mjs';

export const SAFE_ALL_SCOPES = ['core', 'sidecar', 'webgui', 'status'];
export const SCOPE_IDS = [
  'core',
  'sidecar',
  'camofox-deps',
  'camofox-browser',
  'model-service',
  'camofox-service',
  'webgui',
  'status',
];
export const OWNER_MODES = [
  'undecided',
  'host-owned',
  'app-owned',
  'api-key-only',
  'skipped',
];

export function usage(exitCode = 0) {
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

function defaultOptions() {
  const persistedOwnership = readToolOwnership().decisions_by_tool;
  return {
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
}

function parseOwnerOption(options, argv, index) {
  const ownerOptions = [
    ['ollama', '--ollama-owner'],
    ['firecrawl', '--firecrawl-owner'],
    ['camofox', '--camofox-owner'],
  ];
  for (const [tool, optionName] of ownerOptions) {
    const parsed = readValue(argv, index, optionName);
    if (!parsed) {
      continue;
    }
    options.owners[tool] = parseOwner(parsed.value, optionName);
    options.ownerOverrides.add(tool);
    return parsed.nextIndex;
  }
  return null;
}

function parseScopeOrFlag(options, arg) {
  if (arg === '--core') {
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

export function parseArgs(argv) {
  const options = defaultOptions();

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--') {
      continue;
    }
    const nextIndex = parseOwnerOption(options, argv, index);
    if (nextIndex !== null) {
      index = nextIndex;
      continue;
    }
    parseScopeOrFlag(options, arg);
  }

  if (options.openBrowser && !options.selectedScopes.has('webgui')) {
    process.stderr.write(
      '--open-browser requires selecting --webgui or --all.\n',
    );
    usage(2);
  }
  if (options.yes && !options.dryRun && options.selectedScopes.size === 0) {
    process.stderr.write(
      'Select at least one app:up scope before using --yes.\n',
    );
    usage(2);
  }
  if (options.selectedScopes.has('camofox-browser')) {
    options.selectedScopes.add('camofox-deps');
  }

  return options;
}
