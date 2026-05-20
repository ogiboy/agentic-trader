import crypto from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';

function getUserPersistencePaths(profileDir, userId) {
  const rootDir = path.resolve(profileDir);
  const safeUserDir = crypto
    .createHash('sha256')
    .update(String(userId))
    .digest('hex')
    .slice(0, 32);

  const userDir = path.join(rootDir, safeUserDir);
  return {
    rootDir,
    userDir,
    storageStatePath: path.join(userDir, 'storage-state.json'),
    metaPath: path.join(userDir, 'meta.json'),
  };
}

/**
 * Check for and validate a user's persisted storage-state file and return its path.
 *
 * Validates that the file exists and contains a JSON object with a `cookies` array,
 * and, if present, an `origins` array.
 * @param {string|undefined|null} profileDir - Root profile directory; if falsy the function returns `undefined`.
 * @param {string|number} userId - User identifier used to locate the persisted file.
 * @param {{ warn?: Function }=} logger - Optional logger with a `warn` method used for non-ENOENT errors.
 * @returns {string|undefined} The filesystem path to a valid `storage-state.json` when present and valid, `undefined` otherwise.
 */
async function loadPersistedStorageState(profileDir, userId, logger = console) {
  if (!profileDir) return undefined;

  const { storageStatePath } = getUserPersistencePaths(profileDir, userId);

  try {
    const raw = await fs.readFile(storageStatePath, 'utf8');
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') return undefined;
    if (!Array.isArray(parsed.cookies)) return undefined;
    if (parsed.origins !== undefined && !Array.isArray(parsed.origins))
      return undefined;
    return storageStatePath;
  } catch (err) {
    if (err?.code === 'ENOENT') return undefined;
    logger?.warn?.('failed to load persisted storage state', {
      userId: String(userId),
      storageStatePath,
      error: err?.message || String(err),
    });
    return undefined;
  }
}

/**
 * Persist a browser context's storage state and a small metadata file into a per-user directory under the given profile directory.
 *
 * Attempts an atomic write sequence using temporary files and renames: saves the context's storage state to `storage-state.json`
 * and writes a `meta.json` containing `userId`, `updatedAt`, and the storage path. Cleans up temporary files on error.
 *
 * @param {Object} params - Function parameters.
 * @param {string} params.profileDir - Root profile directory where per-user data will be stored. If falsy, persistence is disabled.
 * @param {string|number} params.userId - Identifier for the user; used to derive the per-user directory.
 * @param {Object} params.context - Browser context providing a `storageState({ path })` method to export storage.
 * @param {Object} [params.logger=console] - Optional logger with a `warn` method used for error reporting.
 * @returns {Object} Result of the operation:
 *  - `{ persisted: true, userDir: string, storageStatePath: string, metaPath: string }` on success.
 *  - `{ persisted: false, reason: 'disabled' }` if persistence is disabled (missing `profileDir` or `context`).
 *  - `{ persisted: false, reason: 'error', error: Error }` if an error occurred while persisting.
 */
async function persistStorageState({
  profileDir,
  userId,
  context,
  logger = console,
}) {
  if (!profileDir || !context) {
    return { persisted: false, reason: 'disabled' };
  }

  const { userDir, storageStatePath, metaPath } = getUserPersistencePaths(
    profileDir,
    userId,
  );
  const suffix = `.tmp-${process.pid}-${Date.now()}`;
  const tmpStoragePath = `${storageStatePath}${suffix}`;
  const tmpMetaPath = `${metaPath}${suffix}`;

  try {
    await fs.mkdir(userDir, { recursive: true });
    await context.storageState({ path: tmpStoragePath });
    await fs.rename(tmpStoragePath, storageStatePath);
    await fs.writeFile(
      tmpMetaPath,
      JSON.stringify(
        {
          userId: String(userId),
          updatedAt: new Date().toISOString(),
          storageStatePath,
        },
        null,
        2,
      ),
    );
    await fs.rename(tmpMetaPath, metaPath);
    return { persisted: true, userDir, storageStatePath, metaPath };
  } catch (err) {
    await fs.unlink(tmpStoragePath).catch(() => {});
    await fs.unlink(tmpMetaPath).catch(() => {});
    logger?.warn?.('failed to persist storage state', {
      userId: String(userId),
      storageStatePath,
      error: err?.message || String(err),
    });
    return { persisted: false, reason: 'error', error: err };
  }
}

export {
  getUserPersistencePaths,
  loadPersistedStorageState,
  persistStorageState,
};
