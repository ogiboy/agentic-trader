#!/usr/bin/env node
import {
  parseJsonPayload,
  resolveAgenticTrader,
  runLifecycleCommand,
} from './lib/app-lifecycle.mjs';

/**
 * Write the CLI usage/help text to stdout and exit the process with the provided code.
 * @param {number} exitCode - Process exit code; defaults to 0.
 */
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

/**
 * Parse CLI arguments for the doctor command into an options object.
 *
 * If `-h` or `--help` is present, prints usage and exits. Unknown options are
 * reported to stderr and trigger printing usage with exit code 2. The special
 * marker `--` is ignored.
 *
 * @param {string[]} argv - Command-line arguments to parse (typically process.argv.slice(2)).
 * @returns {{json: boolean}} An options object where `json` is true when `--json` was provided.
 */
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

/**
 * Create a step descriptor for a lifecycle check.
 * @param {string} id - Unique step identifier used in results and output.
 * @param {string} label - Human-readable description shown in summaries.
 * @param {string[]} args - CLI arguments for invoking the step (the entrypoint path is prepended when the command is executed).
 * @returns {{id: string, label: string, args: string[]}} The step descriptor object.
 */
function step(id, label, args) {
  return { id, label, args };
}

/**
 * Provide an ordered list of diagnostic step descriptors used by the app:doctor command.
 *
 * @returns {Array<{id: string, label: string, args: string[]}>} An array of step descriptor objects, each containing:
 * - `id`: a short identifier for the step,
 * - `label`: a human-readable description,
 * - `args`: command arguments to invoke the step.
 */
function doctorSteps() {
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

/**
 * Executes a single lifecycle step using the Agentic Trader CLI and returns a normalized result.
 *
 * @param {string} cliPath - Filesystem path to the agentic-trader CLI executable.
 * @param {{id: string, label: string, args: string[]}} stepInfo - Descriptor for the step: `id`, human `label`, and CLI `args`.
 * @returns {{id: string, label: string, command: string[], mutates: false, status: 'passed'|'failed', exit_code: number, payload: any|null, stdout: string, stderr: string}}
 * An object summarizing the executed step:
 * - `id`, `label`: copied from `stepInfo`.
 * - `command`: full command array executed.
 * - `mutates`: always `false` for doctor checks.
 * - `status`: `'passed'` when the underlying command exit code is 0, `'failed'` otherwise.
 * - `exit_code`: numeric exit code (defaults to `1` if the command exit code is undefined).
 * - `payload`: parsed JSON from stdout when the command succeeded, otherwise `null`.
 * - `stdout`, `stderr`: raw captured output streams.
 */
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

/**
 * List safety notes that describe the read-only, non-invasive nature and scope of app:doctor checks.
 *
 * @returns {string[]} An array of safety note strings explaining that checks are read-only, network-light, and do not modify dependencies, accounts, secrets, or running trading daemons.
 */
function safetyNotes() {
  return [
    'app:doctor is read-only and never starts a trading daemon.',
    'Provider checks are network-light; local model generation probes stay explicit through v1-readiness --provider-check or model-service status --probe-generation.',
    'No dependencies, browser binaries, Ollama models, provider accounts, secrets, brokerage config, or app-owned processes are changed.',
  ];
}

function yesNo(value) {
  return value ? 'yes' : 'no';
}

function payloadSummaryLines(result) {
  const payload = result.payload;
  if (!payload || typeof payload !== 'object') {
    return [];
  }
  if (result.id === 'setup-status') {
    const lines = [];
    if ('core_ready' in payload || 'optional_ready' in payload) {
      lines.push(
        `core_ready=${yesNo(payload.core_ready)} optional_ready=${yesNo(payload.optional_ready)}`,
      );
    }
    const tools = Array.isArray(payload.tools) ? payload.tools : [];
    const degradedTools = tools
      .filter(
        (tool) =>
          tool &&
          typeof tool === 'object' &&
          tool.status &&
          !['available', 'healthy', 'installed'].includes(String(tool.status)),
      )
      .slice(0, 4)
      .map((tool) => `${tool.tool_id || 'tool'}:${tool.status}`);
    if (degradedTools.length > 0) {
      lines.push(`degraded_tools=${degradedTools.join(', ')}`);
    }
    return lines;
  }
  if (
    ['model-service', 'camofox-service', 'webgui-service'].includes(result.id)
  ) {
    const fields = [];
    if ('app_owned' in payload) {
      fields.push(`app_owned=${yesNo(payload.app_owned)}`);
    }
    if ('service_reachable' in payload) {
      fields.push(`service_reachable=${yesNo(payload.service_reachable)}`);
    }
    if (payload.message) {
      fields.push(`message=${String(payload.message)}`);
    }
    return fields.length > 0 ? [fields.join(' ')] : [];
  }
  if (result.id === 'provider-diagnostics') {
    const fields = [];
    if (payload.market_data && typeof payload.market_data === 'object') {
      fields.push(
        `market_provider=${payload.market_data.selected_provider ?? '-'}`,
      );
    }
    if (Array.isArray(payload.warnings)) {
      fields.push(`warnings=${payload.warnings.length}`);
    }
    return fields.length > 0 ? [fields.join(' ')] : [];
  }
  if (result.id === 'v1-readiness') {
    const paperOperations =
      payload.paper_operations && typeof payload.paper_operations === 'object'
        ? payload.paper_operations
        : null;
    const allowed =
      paperOperations && 'allowed' in paperOperations
        ? paperOperations.allowed
        : payload.ready;
    const fields = [`paper_operations_allowed=${yesNo(allowed)}`];
    const checks = Array.isArray(paperOperations?.checks)
      ? paperOperations.checks
      : [];
    const failedChecks = checks
      .filter((check) => check && typeof check === 'object' && !check.passed)
      .slice(0, 4)
      .map((check) => check.name || 'check');
    if (failedChecks.length > 0) {
      fields.push(`failed=${failedChecks.join(', ')}`);
    }
    return [fields.join(' ')];
  }
  return [];
}

/**
 * Render a human-readable doctor report to stdout.
 *
 * If `payload.cli_path` is falsy, prints a setup hint and returns. Otherwise prints one line per step:
 * "ok <id>: <label>" when `status === 'passed'`, "fail <id>: <label>" otherwise.
 *
 * @param {Object} payload - Report payload produced by the doctor run.
 * @param {?string} payload.cli_path - Path to the agentic-trader CLI; when falsy a setup hint is printed.
 * @param {Array<Object>} payload.steps - Ordered step results to render.
 * @param {string} payload.steps[].id - Step identifier.
 * @param {string} payload.steps[].label - Human-readable step label.
 * @param {string} payload.steps[].status - Step status; expected value `"passed"` indicates success.
 */
function renderHuman(payload) {
  process.stdout.write('Agentic Trader app:doctor\n');
  if (!payload.cli_path) {
    process.stdout.write(
      'local agentic-trader entrypoint was not found. Run make setup, set AGENTIC_TRADER_CLI, or set AGENTIC_TRADER_ALLOW_GLOBAL_CLI=1 intentionally.\n',
    );
    return;
  }
  for (const result of payload.steps) {
    process.stdout.write(
      `${result.status === 'passed' ? 'ok' : 'fail'} ${result.id}: ${result.label}\n`,
    );
    for (const line of payloadSummaryLines(result)) {
      process.stdout.write(`  ${line}\n`);
    }
  }
}

/**
 * Execute the app:doctor workflow: run readiness checks, emit results, and terminate the process.
 *
 * Parses command-line options, locates the Agentic Trader CLI, runs the predefined read-only diagnostic steps
 * when the CLI is available, and builds a payload describing the action and step results. Writes pretty JSON
 * to stdout when `--json` is present; otherwise prints a human-readable summary. Exits with status code 0
 * only when the app CLI was found and every step returned exit code 0, otherwise exits with status code 1.
 */
function main() {
  const options = parseArgs(process.argv.slice(2));
  const cliPath = resolveAgenticTrader();
  const steps = cliPath
    ? doctorSteps().map((stepInfo) => runStep(cliPath, stepInfo))
    : [];
  const exitCode =
    cliPath && steps.every((result) => result.exit_code === 0) ? 0 : 1;
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
