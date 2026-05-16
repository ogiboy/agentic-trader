import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, writeFileSync, chmodSync } from 'node:fs';
import { dirname, isAbsolute, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export const ROOT_DIR = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
export const OWNERSHIP_MODES = ['undecided', 'host-owned', 'app-owned', 'api-key-only', 'skipped'];
export const OWNERSHIP_TOOL_IDS = ['ollama', 'firecrawl', 'camofox'];
export const TOOL_OWNERSHIP_SCHEMA_VERSION = 'tool-ownership/v1';

export function commandExists(command) {
  const result = spawnSync('sh', ['-c', 'command -v "$1"', 'sh', command], {
    cwd: ROOT_DIR,
    encoding: 'utf8',
  });
  return result.status === 0 ? result.stdout.trim() : null;
}

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

export function parseJsonPayload(stdout) {
  try {
    return JSON.parse(stdout);
  } catch {
    return null;
  }
}

export function runLifecycleCommand(command, options = {}) {
  return spawnSync(command[0], command.slice(1), {
    cwd: options.cwd ?? ROOT_DIR,
    env: options.env ?? process.env,
    encoding: 'utf8',
    stdio: 'pipe',
  });
}

export function runtimeDir() {
  const configured = process.env.AGENTIC_TRADER_RUNTIME_DIR || 'runtime';
  return isAbsolute(configured) ? configured : resolve(ROOT_DIR, configured);
}

export function toolOwnershipPath() {
  return join(runtimeDir(), 'setup', 'tool-ownership.json');
}

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

export function defaultOwnershipDecision(tool) {
  return {
    tool,
    mode: 'undecided',
    source: 'default',
    updated_at: null,
    note: ownershipNote(tool, 'undecided'),
  };
}

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

export function explicitOwnershipUpdates(owners) {
  return Object.fromEntries(
    Object.entries(owners).filter(([, mode]) => mode && mode !== 'undecided'),
  );
}

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

export function ownershipModeFor(tool) {
  return readToolOwnership().decisions_by_tool[tool]?.mode ?? 'undecided';
}
