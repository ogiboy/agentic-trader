import crypto from 'node:crypto';
import fs from 'node:fs';
import fsp from 'node:fs/promises';
import path from 'node:path';

/**
 * Produce a short, deterministic identifier for a user based on their ID.
 * @param {*} userId - Value identifying the user; will be converted to a string.
 * @returns {string} Hex-encoded SHA-256 digest of `String(userId)`, truncated to the first 16 characters.
 */
function hashUserId(userId) {
  return crypto
    .createHash('sha256')
    .update(String(userId))
    .digest('hex')
    .slice(0, 16);
}

/**
 * Compute the filesystem path for a user's traces subdirectory.
 * @param {string} baseDir - Base directory where per-user trace directories are stored.
 * @param {string|number} userId - User identifier used to derive the directory name.
 * @returns {string} Absolute or relative path to the user's traces subdirectory.
 */
export function userTracesDir(baseDir, userId) {
  return path.join(baseDir, hashUserId(userId));
}

export function ensureTracesDir(baseDir, userId) {
  const dir = userTracesDir(baseDir, userId);
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

export function makeTraceFilename() {
  const ts = new Date().toISOString().replace(/[:.]/g, '-');
  const suffix = crypto.randomBytes(3).toString('hex');
  return `trace-${ts}-${suffix}.zip`;
}

/**
 * Build the filesystem path for a trace file belonging to a specific user.
 * @param {string} baseDir - Root directory where per-user traces are stored.
 * @param {string|number} userId - Identifier for the user; used to derive the user's traces subdirectory.
 * @param {string} filename - Name of the trace file (must be a single filename, not a path).
 * @returns {string} The joined path to the user's traces directory and the provided filename.
 */
export function tracePathFor(baseDir, userId, filename) {
  return path.join(ensureTracesDir(baseDir, userId), filename);
}

/**
 * Resolve a safe absolute path to a user's trace file or return `null` for unsafe names.
 * @param {string} baseDir - Root traces directory.
 * @param {string|number} userId - User identifier used to locate the user's traces subdirectory.
 * @param {string} filename - Trace filename; must be non-empty, must not contain `/`, `\`, `..`, or start with `.`.
 * @returns {string|null} The resolved absolute path within the user's traces directory, or `null` if the filename is invalid or resolves outside the user directory.
 */
export function resolveTracePath(baseDir, userId, filename) {
  if (
    !filename ||
    filename.includes('/') ||
    filename.includes('\\') ||
    filename.includes('..') ||
    filename.startsWith('.') ||
    !filename.endsWith('.zip')
  ) {
    return null;
  }
  const userDir = userTracesDir(baseDir, userId);
  const full = path.join(userDir, filename);
  const resolved = path.resolve(full);
  if (!resolved.startsWith(path.resolve(userDir) + path.sep)) return null;
  return resolved;
}

export async function listUserTraces(baseDir, userId) {
  const dir = userTracesDir(baseDir, userId);
  let names;
  try {
    names = await fsp.readdir(dir);
  } catch {
    return [];
  }
  const out = [];
  for (const name of names) {
    if (!name.endsWith('.zip')) continue;
    const full = path.join(dir, name);
    try {
      const st = await fsp.stat(full);
      if (!st.isFile()) continue;
      out.push({
        filename: name,
        sizeBytes: st.size,
        createdAt: st.birthtimeMs || st.ctimeMs,
        modifiedAt: st.mtimeMs,
      });
    } catch {
      // vanished mid-scan
    }
  }
  out.sort((a, b) => b.modifiedAt - a.modifiedAt);
  return out;
}

export async function statTrace(fullPath) {
  try {
    const st = await fsp.stat(fullPath);
    if (!st.isFile()) return null;
    return st;
  } catch {
    return null;
  }
}

/**
 * Delete the trace file at the given filesystem path.
 * @param {string} fullPath - Absolute path to the `.zip` trace file to remove.
 */
export async function deleteTrace(fullPath) {
  await fsp.unlink(fullPath);
}

/**
 * Remove outdated or oversized trace ZIP files under per-user subdirectories.
 *
 * Scans each user subdirectory of `baseDir` for files ending with `.zip`, deletes files older than `ttlMs` or larger than `maxBytesPerFile`, and accumulates statistics.
 *
 * @param {Object} [options] - Sweep options.
 * @param {string} options.baseDir - Root directory containing per-user trace subdirectories.
 * @param {number} [options.ttlMs] - Time-to-live in milliseconds; files with modified time older than `now - ttlMs` are removed.
 * @param {number} [options.maxBytesPerFile] - Maximum allowed file size in bytes; files larger than this are removed.
 * @param {number} [options.now=Date.now()] - Reference timestamp in milliseconds for TTL comparisons.
 * @returns {{ scanned: number, removedTtl: number, removedOversized: number, bytes: number }} An object summarizing the sweep: `scanned` files examined, `removedTtl` files removed for age, `removedOversized` files removed for size, and `bytes` total freed.
 */
export function sweepOldTraces({
  baseDir,
  ttlMs,
  maxBytesPerFile,
  now = Date.now(),
} = {}) {
  const result = { scanned: 0, removedTtl: 0, removedOversized: 0, bytes: 0 };
  if (!baseDir) return result;

  let userDirs;
  try {
    userDirs = fs.readdirSync(baseDir);
  } catch {
    return result;
  }

  for (const userDir of userDirs) {
    const dir = path.join(baseDir, userDir);
    let st;
    try {
      st = fs.lstatSync(dir);
    } catch {
      continue;
    }
    if (!st.isDirectory()) continue;

    let files;
    try {
      files = fs.readdirSync(dir);
    } catch {
      continue;
    }

    for (const name of files) {
      if (!name.endsWith('.zip')) continue;
      result.scanned++;
      const full = path.join(dir, name);
      try {
        const fst = fs.statSync(full);
        if (!fst.isFile()) continue;
        const tooOld = ttlMs != null && now - fst.mtimeMs > ttlMs;
        const tooBig = maxBytesPerFile != null && fst.size > maxBytesPerFile;
        if (tooOld) {
          fs.unlinkSync(full);
          result.removedTtl++;
          result.bytes += fst.size;
        } else if (tooBig) {
          fs.unlinkSync(full);
          result.removedOversized++;
          result.bytes += fst.size;
        }
      } catch {
        // vanished or permission denied
      }
    }
  }

  return result;
}
