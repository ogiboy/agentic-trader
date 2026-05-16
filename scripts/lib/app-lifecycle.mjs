import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, writeFileSync, chmodSync } from 'node:fs';
import { dirname, isAbsolute, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export const ROOT_DIR = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
export const OWNERSHIP_MODES = ['undecided', 'host-owned', 'app-owned', 'api-key-only', 'skipped'];
export const OWNERSHIP_TOOL_IDS = ['ollama', 'firecrawl', 'camofox'];
export const TOOL_OWNERSHIP_SCHEMA_VERSION = 'tool-ownership/v1';

/**
 * Determine the path of an executable available in the shell PATH.
 * @param {string} command - The command name to look up (e.g., "git").
 * @returns {string|null} The resolved path to the command if found, `null` otherwise.
 */
export function commandExists(command) {
  const result = spawnSync('sh', ['-c', 'command -v "$1"', 'sh', command], {
    cwd: ROOT_DIR,
    encoding: 'utf8',
  });
  return result.status === 0 ? result.stdout.trim() : null;
}

/**
 * Locate the agentic-trader CLI entrypoint, preferring an environment override and a local worktree before falling back to a PATH lookup.
 * @returns {string|null} The resolved entrypoint path if available, otherwise `null`.
 */
export function resolveAgenticTrader() {
  if (Object.prototype.hasOwnProperty.call(process.env, 'AGENTIC_TRADER_CLI')) {
    return process.env.AGENTIC_TRADER_CLI || null;
  }
  const worktreeEntrypoint = join(ROOT_DIR, '.venv/bin/agentic-trader');
  if (existsSync(worktreeEntrypoint)) {
    return worktreeEntrypoint;
  }
  return commandExists('agentic-trader');
}

/**
 * Parse a JSON string and return the resulting value.
 * @param {string} stdout - JSON-formatted text to parse.
 * @returns {*} The parsed value, or `null` if the input is not valid JSON.
 */
export function parseJsonPayload(stdout) {
  try {
    return JSON.parse(stdout);
  } catch {
    return null;
  }
}

/**
 * Execute a lifecycle command and capture its exit status and I/O.
 * @param {string[]} command - An array where the first element is the executable and the rest are its arguments.
 * @param {{cwd?: string, env?: NodeJS.ProcessEnv}} [options] - Optional execution context: `cwd` overrides working directory (defaults to project root), `env` overrides environment variables (defaults to process.env).
 * @returns {import('child_process').SpawnSyncReturns<string>} The spawnSync result object containing `status`, `stdout`, `stderr`, `pid`, `signal`, and related fields.
 */
export function runLifecycleCommand(command, options = {}) {
  return spawnSync(command[0], command.slice(1), {
    cwd: options.cwd ?? ROOT_DIR,
    env: options.env ?? process.env,
    encoding: 'utf8',
    stdio: 'pipe',
  });
}

/**
 * Determine the runtime directory path used by the app.
 *
 * Reads the AGENTIC_TRADER_RUNTIME_DIR environment variable (defaulting to "runtime") and returns it as an absolute path; if the configured value is relative it is resolved against the repository root.
 * @returns {string} The absolute path to the runtime directory.
 */
export function runtimeDir() {
  const configured = process.env.AGENTIC_TRADER_RUNTIME_DIR || 'runtime';
  return isAbsolute(configured) ? configured : resolve(ROOT_DIR, configured);
}

/**
 * Get the filesystem path to the persisted tool ownership state file.
 *
 * @returns {string} The absolute path to runtime/setup/tool-ownership.json.
 */
export function toolOwnershipPath() {
  return join(runtimeDir(), 'setup', 'tool-ownership.json');
}

/**
 * Return a human-readable ownership note for a given tool and mode.
 *
 * @param {string} tool - Tool identifier (e.g., 'ollama', 'firecrawl', 'camofox').
 * @param {string} mode - Ownership mode; one of: 'undecided', 'host-owned', 'app-owned', 'api-key-only', 'skipped'.
 * @returns {string} A human-readable note describing the ownership implications for the specified tool and mode.
 */
export function ownershipNote(tool, mode) {
  const notes = {
    'undecided': 'No ownership decision is recorded yet; setup may report degraded readiness instead of claiming this helper.',
    'host-owned': 'Use a host-managed tool or endpoint; app lifecycle commands must not install, start, stop, update, or delete it.',
    'app-owned': 'The app may manage repo/local loopback helper setup or service state only through explicit lifecycle commands.',
    'api-key-only': 'Use ignored environment/keychain credentials only; no CLI install or local service ownership is implied.',
    skipped: 'Keep this helper disabled or degraded; core paper-first workflows must remain understandable without it.',
  };
  if (tool === 'firecrawl' && mode === 'app-owned') {
    return 'Firecrawl app-owned uses the repo dependency path first; credentials still belong in ignored env/keychain state and host CLI fallback requires host-owned mode.';
  }
  return notes[mode] ?? notes.undecided;
}

/**
 * Create a default ownership decision object for a tool.
 * @param {string} tool - The tool identifier (e.g., 'ollama', 'firecrawl', 'camofox').
 * @returns {{tool: string, mode: string, source: string, updated_at: null, note: string}} An ownership decision with:
 *  - `tool`: the provided tool identifier,
 *  - `mode`: `'undecided'`,
 *  - `source`: `'default'`,
 *  - `updated_at`: `null`,
 *  - `note`: a human-readable ownership note for the `undecided` mode.
 */
export function defaultOwnershipDecision(tool) {
  return {
    tool,
    mode: 'undecided',
    source: 'default',
    updated_at: null,
    note: ownershipNote(tool, 'undecided'),
  };
}

/**
 * Read the persisted tool-ownership state file and produce a normalized view of ownership decisions for each supported tool.
 *
 * The returned object includes the schema version and path of the state file, the file-level updated timestamp (if present),
 * an array of normalized per-tool decision objects, and a map of those decisions keyed by tool id.
 *
 * @returns {{schema_version: string, state_path: string, updated_at: string|null, decisions: Array<{tool: string, mode: string, source: string, updated_at: string|null, note: string}>, decisions_by_tool: Record<string, {tool: string, mode: string, source: string, updated_at: string|null, note: string}>}} An object describing the persisted ownership state and normalized decisions for each known tool.
 */
export function readToolOwnership() {
  const statePath = toolOwnershipPath();
  let updatedAt = null;
  let records = {};
  if (existsSync(statePath)) {
    try {
      const payload = JSON.parse(readFileSync(statePath, 'utf8'));
      if (payload && typeof payload === 'object') {
        updatedAt = typeof payload.updated_at === 'string' ? payload.updated_at : null;
        records = payload.decisions && typeof payload.decisions === 'object'
          ? payload.decisions
          : {};
      }
    } catch {
      records = {};
    }
  }
  const decisions = OWNERSHIP_TOOL_IDS.map((tool) => {
    const record = records[tool] && typeof records[tool] === 'object' ? records[tool] : {};
    const rawMode = typeof record.mode === 'string' ? record.mode : 'undecided';
    const mode = OWNERSHIP_MODES.includes(rawMode) ? rawMode : 'undecided';
    return {
      tool,
      mode,
      source: typeof record.source === 'string' ? record.source : 'default',
      updated_at: typeof record.updated_at === 'string' ? record.updated_at : null,
      note: ownershipNote(tool, mode),
    };
  });
  return {
    schema_version: TOOL_OWNERSHIP_SCHEMA_VERSION,
    state_path: statePath,
    updated_at: updatedAt,
    decisions,
    decisions_by_tool: Object.fromEntries(decisions.map((decision) => [decision.tool, decision])),
  };
}

/**
 * Produce a map containing only explicit (non-'undecided') ownership decisions.
 *
 * @param {Object<string, string>} owners - Map of tool IDs to ownership mode strings.
 * @returns {Object<string, string>} A new map with entries where the mode is truthy and not 'undecided'.
 */
export function explicitOwnershipUpdates(owners) {
  return Object.fromEntries(
    Object.entries(owners).filter(([, mode]) => mode && mode !== 'undecided'),
  );
}

/**
 * Persist explicit ownership mode updates to the tool-ownership state file and return the resulting state.
 *
 * Applies only entries from `updates` whose mode is set and not `"undecided"`, merges them with existing
 * non-undecided decisions, writes the updated decisions to the runtime tool-ownership JSON file, and
 * attempts to restrict parent directory and file permissions to owner-only in a best-effort manner.
 *
 * @param {Object<string,string>} updates - Map of tool id to ownership mode to persist (e.g., { ollama: "app-owned" }).
 * @param {string} [source='app-up'] - Source label to record for the applied updates.
 * @returns {{ mutated: boolean, payload: Object }} An object with `mutated` indicating whether a write occurred and
 *          `payload` containing the normalized ownership state as returned by `readToolOwnership()`.
 */
export function persistToolOwnership(updates, source = 'app-up') {
  const explicit = explicitOwnershipUpdates(updates);
  if (Object.keys(explicit).length === 0) {
    return { mutated: false, payload: readToolOwnership() };
  }
  const current = readToolOwnership();
  const now = new Date().toISOString();
  const records = {};
  for (const decision of current.decisions) {
    if (decision.mode !== 'undecided') {
      records[decision.tool] = {
        mode: decision.mode,
        source: decision.source,
        updated_at: decision.updated_at ?? now,
      };
    }
  }
  for (const [tool, mode] of Object.entries(explicit)) {
    records[tool] = { mode, source, updated_at: now };
  }
  const statePath = toolOwnershipPath();
  mkdirSync(dirname(statePath), { recursive: true, mode: 0o700 });
  const payload = {
    schema_version: TOOL_OWNERSHIP_SCHEMA_VERSION,
    updated_at: now,
    decisions: records,
  };
  writeFileSync(statePath, `${JSON.stringify(payload, null, 2)}\n`, {
    encoding: 'utf8',
    mode: 0o600,
  });
  try {
    chmodSync(dirname(statePath), 0o700);
    chmodSync(statePath, 0o600);
  } catch {
    // Best-effort owner-only permissions; runtime still reports the state path.
  }
  return { mutated: true, payload: readToolOwnership() };
}

/**
 * Get the recorded ownership mode for a given tool.
 * @param {string} tool - Tool identifier (e.g. one of OWNERSHIP_TOOL_IDS).
 * @returns {string} One of `undecided`, `host-owned`, `app-owned`, `api-key-only`, or `skipped`; defaults to `undecided` when no decision is recorded.
 */
export function ownershipModeFor(tool) {
  return readToolOwnership().decisions_by_tool[tool]?.mode ?? 'undecided';
}
