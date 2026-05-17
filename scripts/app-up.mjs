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

/**
 * Print the CLI usage/help text and terminate the process.
 * @param {number} exitCode - Exit code passed to process.exit; defaults to 0.
 */
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

/**
 * Parses an ownership-like CLI option from argv at the given index.
 *
 * Supports both `--option=value` and `--option value` forms. If the option is present
 * and a value is provided, returns an object with the parsed `value` and the `nextIndex`
 * pointing to the last consumed argv index. If the option is not present at `index`,
 * returns `null`. On a missing or invalid value the function writes an error message
 * to stderr and calls `usage(2)`.
 *
 * @param {string[]} argv - The CLI arguments array.
 * @param {number} index - The index within `argv` to inspect.
 * @param {string} optionName - The exact option name to match (e.g. `--ollama-owner`).
 * @returns {{ value: string, nextIndex: number } | null} An object with `value` and `nextIndex` when the option is parsed, or `null` if the current arg is not this option.
 */
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

/**
 * Validate an ownership mode value for a CLI owner option.
 *
 * If `value` is not one of the allowed modes or is `"undecided"`, an error
 * message is written to stderr and `usage(2)` is invoked (which will terminate
 * the process). Otherwise returns the validated mode.
 *
 * @param {string} value - The ownership mode to validate.
 * @param {string} optionName - The CLI option name used in the error message.
 * @returns {string} The validated ownership mode.
 */
function parseOwner(value, optionName) {
  if (!OWNER_MODES.includes(value) || value === 'undecided') {
    process.stderr.write(
      `${optionName} must be one of: host-owned, app-owned, api-key-only, skipped.\n`,
    );
    usage(2);
  }
  return value;
}

/**
 * Parse CLI arguments for the app-up guided workflow and produce a normalized options object used by the planner and executor.
 * @param {string[]} argv - Array of command-line arguments to parse (typically process.argv.slice(2)).
 * @returns {{ dryRun: boolean, json: boolean, openBrowser: boolean, owners: { ollama: string, firecrawl: string, camofox: string }, ownerOverrides: Set<string>, selectedScopes: Set<string>, yes: boolean }} An options object:
 *  - dryRun: true when planning only (no execution).
 *  - json: true when output should be machine-readable JSON.
 *  - openBrowser: true when the webgui step should open a browser.
 *  - owners: current ownership mode for each tool (defaults from persisted state or 'undecided').
 *  - ownerOverrides: set of tool keys whose ownership was explicitly provided on the command line.
 *  - selectedScopes: set of scope ids requested via flags (e.g., 'core', 'webgui', etc.).
 *  - yes: true when the user approved execution (enables non-dry-run execution when combined with dryRun=false).
 */
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

/**
 * Create a standardized "up" step descriptor used in the guided first-run plan.
 *
 * @param {string} id - Unique step identifier.
 * @param {string} label - Human-readable step label.
 * @param {string} command - Shell/CLI command to run for this step.
 * @param {string} scope - Logical scope this step belongs to (e.g., "core", "webgui").
 * @param {object} [options] - Optional step overrides.
 * @param {string} [options.cwd] - Working directory for the command; defaults to the repository root.
 * @param {boolean} [options.mutates=true] - Whether a successful run is considered to have mutated system state.
 * @param {string} [options.reason] - Short note explaining the step when presented in plans or summaries.
 * @param {{tool:string,mode:string}} [options.requiresOwner] - Ownership requirement for selecting/executing the step.
 * @param {boolean} [options.largeDownload=false] - Marks the step as a large download operation.
 * @returns {object} Step descriptor with fields:
 *   - `id`, `label`, `command`, `cwd`, `scope`
 *   - `mutates` (boolean), `selected` (boolean, initially false)
 *   - `reason` (string|undefined), `requires_owner` (object|undefined)
 *   - `large_download` (boolean)
 */
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

/**
 * Build the ordered list of guided "up" steps used by the first-run workflow.
 *
 * @param {Object} options - Runtime options used to tailor the plan.
 * @param {boolean} [options.openBrowser] - When true, includes `--open-browser` in the web GUI start command.
 * @returns {Array<Object>} An ordered array of step descriptors. Each step contains standardized fields such as
 * `id`, `label`, `command`, `cwd`, `scope`, `mutates`, `selected`, and optional `reason`, `requiresOwner`, and `largeDownload`.
 */
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

/**
 * Provide human-readable safety notes describing dry-run behavior and limits of the guided first-run flow.
 * @returns {string[]} An array of safety note strings explaining that the command defaults to a dry-run, which scopes and ownership decisions are required to execute changes, and which external systems or resources will not be modified by the guided flow.
 */
function safetyNotes() {
  return [
    'app:up defaults to a dry-run plan.',
    'Executing first-run setup requires explicit scopes plus --yes.',
    'The guided flow composes existing lifecycle commands instead of owning a second runtime.',
    'No trading daemon, live broker, provider account, secret, brokerage config, hidden model pull, or hidden browser download is changed.',
    'Camofox browser binary fetch and optional model/Camofox service starts require explicit scopes and app-owned ownership decisions.',
  ];
}

/**
 * Create a human-readable ownership decision record for a given tool and mode.
 *
 * @param {string} tool - Tool identifier (e.g., `ollama`, `firecrawl`, `camofox`).
 * @param {string} mode - Ownership mode identifier (one of `undecided`, `host-owned`, `app-owned`, `api-key-only`, `skipped`).
 * @returns {{tool: string, mode: string, note: string}} An object containing the original `tool` and `mode` plus a `note` explaining the selected ownership mode.
 */
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

/**
 * Builds the ownership decision records for the known tools.
 * @param {Object} options - CLI options and state.
 * @param {Object} options.owners - Mapping of tool -> ownership mode.
 * @returns {Array<Object>} An array of ownership decision objects (one each for `ollama`, `firecrawl`, and `camofox`). Each object has `tool`, `mode`, and `note` fields. 
 */
function ownershipDecisions(options) {
  return [
    ownerDecision('ollama', options.owners.ollama),
    ownerDecision('firecrawl', options.owners.firecrawl),
    ownerDecision('camofox', options.owners.camofox),
  ];
}

/**
 * Build a mapping of ownership updates only for tools that were explicitly overridden.
 *
 * @param {Object} options - Options bag for the current run.
 * @param {Object<string,string>} options.owners - Current owner mode per tool (e.g., `{ ollama: 'app-owned' }`).
 * @param {Set<string>} options.ownerOverrides - Set of tool names whose ownership was explicitly provided on the CLI.
 * @returns {Object<string,string>} An object mapping each overridden tool name to its chosen owner mode.
 */
function ownershipUpdates(options) {
  return Object.fromEntries(
    [...options.ownerOverrides].map((tool) => [tool, options.owners[tool]]),
  );
}

/**
 * Mark steps whose scope is present in `selectedScopes` as selected.
 * @param {Array<Object>} plan - Ordered list of step objects.
 * @param {Set<string>} selectedScopes - Set of scope ids to select.
 * @returns {Array<Object>} The plan with each step's `selected` property set to `true` if its scope is in `selectedScopes`, otherwise `false`.
 */
function selectSteps(plan, selectedScopes) {
  return plan.map((step) => ({
    ...step,
    selected: selectedScopes.has(step.scope),
  }));
}

/**
 * Determine whether a step is blocked by the current tool ownership choices.
 *
 * @param {Object} step - Step object which may include `requires_owner` and `scope`.
 * @param {{[tool:string]: string}} owners - Mapping of tool names to chosen ownership modes.
 * @returns {string|null} A human-readable blocker message when the step is blocked, or `null` when the step is not blocked.
 */
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

/**
 * Produce a pre-execution record for a plan step, reflecting selection and ownership blockers.
 * @param {object} step - A step object from the plan (fields: id, label, command, scope, selected, mutates, reason, requires_owner, etc.).
 * @param {Set<string>} selectedScopes - Set of scope ids that were selected for execution.
 * @param {Object<string,string>} owners - Current tool ownership decisions keyed by tool name.
 * @returns {object} A step record containing the original step fields plus:
 *  - `status`: `'planned'`, `'deferred'`, or `'blocked'` depending on selection and ownership,
 *  - `reason`: blocker message when blocked or the step's original reason,
 *  - `exit_code`: `1` when blocked, otherwise `null`,
 *  - `stdout` and `stderr`: initialized as empty strings.
 */
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

/**
 * Create a step record representing a skipped step.
 * @param {object} step - Original step object whose fields are preserved.
 * @param {string} reason - Human-readable explanation why the step was skipped.
 * @return {object} A step record with `status` set to `'skipped'`, `reason` set to the provided message, `exit_code` set to `null`, and empty `stdout`/`stderr`.
 */
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

/**
 * Create a step record marked as blocked for reporting.
 * @param {Object} step - The original step object to copy and annotate.
 * @param {string} reason - Human-readable reason why the step is blocked.
 * @returns {Object} A new step object with `status: 'blocked'`, the provided `reason`, `exit_code: 1`, and empty `stdout`/`stderr`.
 */
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

/**
 * Execute a lifecycle step command and return a structured result describing its outcome.
 * @param {Object} step - Step descriptor containing at minimum `command` (string) and `cwd` (string) used to run the command.
 * @returns {Object} Result object that merges the original step fields and adds:
 *   - `status` — `'passed'` if the command exited with code 0, `'failed'` otherwise.
 *   - `exit_code` — numeric exit code from the command (1 if unavailable).
 *   - `payload` — parsed JSON payload from stdout when the command succeeded, `null` otherwise.
 *   - `stdout` — captured standard output as a string.
 *   - `stderr` — captured standard error as a string.
 */
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

/**
 * Build the execution payload and exit code for the guided "app up" workflow based on provided options.
 *
 * @param {Object} options - Parsed CLI/runtime options that control planning and execution.
 * @param {Set<string>} options.selectedScopes - Scopes explicitly selected for execution.
 * @param {boolean} options.yes - Whether the user approved actual execution (not a dry run).
 * @param {boolean} options.dryRun - Whether dry-run mode was requested.
 * @param {Object} options.owners - Current tool ownership decisions keyed by tool name.
 * @param {boolean} options.openBrowser - Whether the webgui step should open the browser.
 * @returns {{ payload: Object, exitCode: number }} An object containing:
 *  - `payload`: a machine-readable payload describing action metadata (`action`, `mode`, `dry_run`, `approved`),
 *    whether any ownership/service state was mutated, the list of selected scopes, ownership decisions and tool
 *    ownership state, safety notes, the full ordered `steps` array with per-step status/output, and suggested
 *    `next_commands`.
 *  - `exitCode`: numeric exit code (0 when all selected executed steps passed; 1 if any selected step failed or was blocked).
 */
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

/**
 * Write a human-readable summary of the guided up payload to stdout.
 *
 * Prints the script title, dry-run status, selected scopes, ownership decisions,
 * and each step's status, id, label, and optional reason. When `payload.dry_run`
 * is true, prints a recommended safe first-run command.
 *
 * @param {Object} payload - Orchestration payload produced by buildPayload.
 *   Expected properties:
 *     - {boolean} dry_run
 *     - {boolean} [dry_run]
 *     - {Array<string>} selected_scopes
 *     - {Array<{tool:string,mode:string}>} ownership_decisions
 *     - {Array<{id:string,label:string,status:string,reason?:string}>} steps
 */
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

/**
 * Run the CLI: parse command-line arguments, build the guided up payload, render output, and terminate the process.
 *
 * Parses options from process.argv, constructs the execution payload, writes machine-readable JSON when `--json`
 * is set or a human-readable summary otherwise, and exits with the computed exit code.
 */
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
