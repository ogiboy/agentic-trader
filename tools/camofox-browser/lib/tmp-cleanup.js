import fs from 'fs';
import path from 'path';
import os from 'os';

const ORPHAN_PATTERNS = [/^\.fea5[a-f0-9]+\.so$/, /^\.5ef7[a-f0-9]+\.node$/];

// Firefox temp profile directories created by Playwright/Camoufox
const FIREFOX_PROFILE_PATTERN = /^playwright_firefoxdev_profile-/;
// Camoufox also creates these
const CAMOUFOX_TMP_PATTERN = /^camoufox[-_]/;

/**
 * Removes orphaned native-module temp files that match known filename patterns and are older than a specified age.
 * @param {Object} [opts] - Options.
 * @param {string} [opts.tmpDir] - Directory to scan; if falsy, the function performs no work.
 * @param {number} [opts.minAgeMs=300000] - Minimum file age in milliseconds required for removal.
 * @param {number} [opts.now=Date.now()] - Reference timestamp in milliseconds used to evaluate file age.
 * @returns {{scanned: number, removed: number, bytes: number, skipped: number}} Summary counts: `scanned` entries matching orphan patterns, `removed` files deleted, total `bytes` freed, and `skipped` entries that were too recent.
 */
export function cleanupOrphanedTempFiles({
  tmpDir,
  minAgeMs = 5 * 60 * 1000,
  now = Date.now(),
} = {}) {
  const result = { scanned: 0, removed: 0, bytes: 0, skipped: 0 };
  if (!tmpDir) return result;

  let entries;
  try {
    entries = fs.readdirSync(tmpDir);
  } catch {
    return result;
  }

  for (const name of entries) {
    if (!ORPHAN_PATTERNS.some((re) => re.test(name))) continue;
    result.scanned++;
    const full = path.join(tmpDir, name);
    try {
      const st = fs.statSync(full);
      if (!st.isFile()) continue;
      if (now - st.mtimeMs < minAgeMs) {
        result.skipped++;
        continue;
      }
      fs.unlinkSync(full);
      result.removed++;
      result.bytes += st.size;
    } catch {
      // file vanished, permission denied, or race with another process - skip silently
    }
  }

  return result;
}

/**
 * Remove stale Playwright/Camoufox Firefox temporary profile directories from the system temp directory.
 *
 * Scans the provided temp directory (or the OS temp directory when `tmpDir` is omitted) for entries matching
 * known Firefox/Camoufox profile/name patterns and deletes directories whose modification time is older than
 * `minAgeMs`. Deletions are best-effort and individual failures are skipped.
 *
 * @param {Object} [opts] - Options.
 * @param {string} [opts.tmpDir] - Directory to scan; uses the OS temp directory when omitted.
 * @param {number} [opts.minAgeMs=120000] - Minimum age in milliseconds for a profile to be considered stale.
 * @param {number} [opts.now=Date.now()] - Reference timestamp (milliseconds since epoch) used to measure age.
 * @returns {{scanned: number, removed: number, bytes: number, skipped: number}} Summary of the cleanup:
 *          `scanned` — number of matching entries inspected,
 *          `removed` — number of directories deleted,
 *          `bytes` — total bytes freed (best-effort),
 *          `skipped` — number of entries skipped due to being too recent.
 */
export function cleanupStaleFirefoxProfiles({
  tmpDir,
  minAgeMs = 2 * 60 * 1000,
  now = Date.now(),
} = {}) {
  const dir = tmpDir || os.tmpdir();
  const result = { scanned: 0, removed: 0, bytes: 0, skipped: 0 };

  let entries;
  try {
    entries = fs.readdirSync(dir);
  } catch {
    return result;
  }

  for (const name of entries) {
    if (!FIREFOX_PROFILE_PATTERN.test(name) && !CAMOUFOX_TMP_PATTERN.test(name))
      continue;
    result.scanned++;
    const full = path.join(dir, name);
    try {
      const st = fs.statSync(full);
      if (!st.isDirectory()) continue;
      if (now - st.mtimeMs < minAgeMs) {
        result.skipped++;
        continue;
      }
      // Calculate directory size before removing
      const dirBytes = _dirSizeSync(full);
      fs.rmSync(full, { recursive: true, force: true, maxRetries: 3 });
      result.removed++;
      result.bytes += dirBytes;
    } catch {
      // directory vanished, permission denied, or in-use -- skip
    }
  }

  return result;
}

/**
 * Compute the total size in bytes of a directory and its contents using a best-effort synchronous scan that skips entries it cannot read.
 * @param {string} dirPath - Path of the directory to measure.
 * @returns {number} Total size in bytes of all readable files under `dirPath`; unreadable entries are ignored.
 */
function _dirSizeSync(dirPath) {
  let total = 0;
  try {
    const entries = fs.readdirSync(dirPath, { withFileTypes: true });
    for (const entry of entries) {
      const full = path.join(dirPath, entry.name);
      try {
        if (entry.isDirectory()) {
          total += _dirSizeSync(full);
        } else {
          total += fs.statSync(full).size;
        }
      } catch {
        /* skip */
      }
    }
  } catch {
    /* skip */
  }
  return total;
}
