/**
 * Download capture and DOM image extraction for camofox-browser.
 *
 * Handles Playwright download events, temp file lifecycle, and
 * in-page image source extraction with optional inline data.
 */

import crypto from 'node:crypto';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';

const MAX_DOWNLOAD_RECORDS_PER_TAB = 20;
const MAX_DOWNLOAD_INLINE_BYTES = 20 * 1024 * 1024;

/**
 * Produce a filesystem-safe filename string from an input value.
 *
 * Converts the input to a string (falling back to "download.bin"), replaces characters illegal
 * in filenames (\, /, :, *, ?, ", <, >, | and control characters U+0000–U+001F) with underscores,
 * trims surrounding whitespace, and truncates the result to at most 200 characters. If the
 * final result is empty, returns "download.bin".
 *
 * @param {*} value - The value to convert into a sanitized filename.
 * @returns {string} A sanitized filename suitable for use on most filesystems.
 */
function sanitizeFilename(value) {
  return (
    String(value || 'download.bin')
      .replace(/[\\/:*?"<>|\u0000-\u001F]/g, '_')
      .trim()
      .slice(0, 200) || 'download.bin'
  );
}

/**
 * Infer a MIME type from a filename or path.
 * @param {string} value - The filename or file path to examine; may be empty or non-string.
 * @returns {string} The guessed MIME type (e.g. `image/png`, `image/jpeg`), or `application/octet-stream` if no known extension is found.
 */
function guessMimeTypeFromName(value) {
  const normalized = String(value || '').toLowerCase();
  if (normalized.endsWith('.png')) return 'image/png';
  if (normalized.endsWith('.jpg') || normalized.endsWith('.jpeg'))
    return 'image/jpeg';
  if (normalized.endsWith('.webp')) return 'image/webp';
  if (normalized.endsWith('.gif')) return 'image/gif';
  if (normalized.endsWith('.svg')) return 'image/svg+xml';
  return 'application/octet-stream';
}

async function removeDownloadFileIfPresent(record) {
  const filePath = record?.filePath;
  if (!filePath) return;
  await fs.unlink(filePath).catch(() => {});
}

/**
 * Enforces the per-tab download retention limit by removing the oldest download records.
 *
 * Removes oldest entries from `tabState.downloads` until its length is at most
 * `MAX_DOWNLOAD_RECORDS_PER_TAB`; for each removed record, deletes the associated
 * temporary file if one exists.
 *
 * @param {Object} tabState - Tab state object containing a `downloads` array of records.
 *   Each record may include a `filePath` property pointing to a temporary file to be removed.
 */
async function trimTabDownloads(tabState) {
  while (tabState.downloads.length > MAX_DOWNLOAD_RECORDS_PER_TAB) {
    const stale = tabState.downloads.shift();
    await removeDownloadFileIfPresent(stale);
  }
}

/**
 * Clears the tab's stored download records and deletes any associated temporary files.
 * @param {object} tabState - The tab state object whose `downloads` will be cleared. If `downloads` is not an array, it will be treated as empty.
 */
async function clearTabDownloads(tabState) {
  const entries = Array.isArray(tabState.downloads)
    ? [...tabState.downloads]
    : [];
  tabState.downloads = [];
  await Promise.all(entries.map(removeDownloadFileIfPresent));
}

async function clearSessionDownloads(session) {
  if (!session || !session.tabGroups) return;
  const tasks = [];
  for (const group of session.tabGroups.values()) {
    for (const tabState of group.values()) {
      tasks.push(clearTabDownloads(tabState));
    }
  }
  await Promise.all(tasks);
}

/**
 * Attach a Playwright download handler to a tab that captures downloads, saves them to a temp file, and records metadata on the tab state.
 *
 * The attachment is idempotent — if a download listener is already attached for the tab, this function returns without change. When downloads occur the handler records an entry in `tabState.downloads`, may add the source URL to `tabState.visitedUrls`, emits optional plugin events for start/complete, and enforces the per-tab retention limit.
 * @param {object} tabState - Tab-local state object (must contain `page`, `downloads`, and `visitedUrls`).
 * @param {string} tabId - Identifier of the tab to associate with recorded downloads.
 * @param {function(string,string,object=):void} log - Logging function accepting level, message, and optional metadata.
 * @param {EventEmitter|undefined|null} pluginEvents - Optional event emitter used to emit `tab:download:start` and `tab:download:complete` events.
 * @param {string|undefined|null} userId - Optional user identifier included in emitted plugin event payloads.
 */
function attachDownloadListener(tabState, tabId, log, pluginEvents, userId) {
  if (tabState.downloadListenerAttached) return;
  tabState.downloadListenerAttached = true;

  tabState.page.on('download', async (download) => {
    const downloadId = crypto.randomUUID();
    const suggestedFilename = sanitizeFilename(
      download.suggestedFilename?.() || `download-${downloadId}.bin`,
    );
    const filePath = path.join(
      os.tmpdir(),
      `camofox-download-${downloadId}-${suggestedFilename}`,
    );

    const url = String(download.url?.() || '').trim();
    if (pluginEvents) {
      pluginEvents.emit('tab:download:start', {
        userId: userId || null,
        tabId,
        filename: suggestedFilename,
        url,
      });
    }

    let failure = null;
    let bytes = null;

    try {
      await download.saveAs(filePath);
      const stat = await fs.stat(filePath);
      bytes = stat.size;
    } catch (err) {
      failure = String(err?.message || err || 'download_save_failed');
      await fs.unlink(filePath).catch(() => {});
    }

    const reportedFailure = await download.failure().catch(() => null);
    if (reportedFailure) {
      failure = reportedFailure;
    }

    if (url) {
      tabState.visitedUrls.add(url);
    }

    const mimeType =
      guessMimeTypeFromName(suggestedFilename) || guessMimeTypeFromName(url);
    tabState.downloads.push({
      id: downloadId,
      tabId,
      url,
      suggestedFilename,
      mimeType,
      bytes,
      createdAt: new Date().toISOString(),
      filePath: failure ? null : filePath,
      failure,
    });

    if (pluginEvents && !failure) {
      pluginEvents.emit('tab:download:complete', {
        userId: userId || null,
        tabId,
        filename: suggestedFilename,
        path: filePath,
        size: bytes,
      });
    }

    await trimTabDownloads(tabState);
    log('info', 'download captured', {
      tabId,
      downloadId,
      suggestedFilename,
      mimeType,
      bytes,
      hasUrl: Boolean(url),
      failure,
    });
  });
}

/**
 * Produce a list of download records for a tab, optionally embedding file data.
 *
 * Creates an array of download item objects reflecting the tab's recorded downloads.
 * Each item always includes `id`, `url`, `suggestedFilename`, `mimeType`, `bytes`, `createdAt`, and `failure`.
 * When `includeData` is true and the download file exists and has no `failure`, items may also include:
 * - `dataBase64` — the file contents encoded as a base64 string;
 * - `dataSkipped` — the literal string `"max_bytes_exceeded"` when the file size exceeds `maxBytes`;
 * - `readError` — an error message string if reading the file failed.
 *
 * @param {Object} tabState - Tab state object that holds download records (expected at `tabState.downloads`).
 * @param {Object} [options] - Options controlling inclusion of inline data.
 * @param {boolean} [options.includeData=false] - If true, attempt to include base64-encoded file data when available.
 * @param {number} [options.maxBytes=MAX_DOWNLOAD_INLINE_BYTES] - Maximum file size (in bytes) allowed for inline inclusion.
 * @returns {Array<Object>} Array of download item objects as described above.
 */
async function getDownloadsList(
  tabState,
  { includeData = false, maxBytes = MAX_DOWNLOAD_INLINE_BYTES } = {},
) {
  const snapshot = Array.isArray(tabState.downloads)
    ? [...tabState.downloads]
    : [];
  const downloads = [];

  for (const entry of snapshot) {
    const item = {
      id: entry.id,
      url: entry.url,
      suggestedFilename: entry.suggestedFilename,
      mimeType: entry.mimeType,
      bytes: entry.bytes,
      createdAt: entry.createdAt,
      failure: entry.failure,
    };

    if (includeData && entry.filePath && !entry.failure) {
      if (typeof entry.bytes === 'number' && entry.bytes > maxBytes) {
        item.dataSkipped = 'max_bytes_exceeded';
      } else {
        try {
          const raw = await fs.readFile(entry.filePath);
          item.dataBase64 = raw.toString('base64');
        } catch (err) {
          item.readError = String(
            err?.message || err || 'download_read_failed',
          );
        }
      }
    }

    downloads.push(item);
  }

  return downloads;
}

export {
  attachDownloadListener,
  clearSessionDownloads,
  clearTabDownloads,
  getDownloadsList,
  guessMimeTypeFromName,
  MAX_DOWNLOAD_INLINE_BYTES,
  sanitizeFilename,
};
