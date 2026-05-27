// lib/resources.js -- Process resource metrics and proxy error classification.
// Isolated from reporter.js so that fs reads and network sends are never
// in the same file (keeps fs reads and network sends in separate modules).

import fs from 'node:fs';

// ============================================================================
// Process resource snapshot (memory, handles, FDs, browser RSS)
// ============================================================================

/**
 * Collect current process (and optionally browser) resource metrics as an anonymized numeric snapshot.
 *
 * @param {Object} [opts] - Optional probes and caller-provided counts.
 * @param {number} [opts.browserPid] - If a positive integer and running on Linux, attempt to read the browser process RSS (kB -> rounded MB). Failures are swallowed.
 * @param {number} [opts.sessionCount] - If provided, included as `browserContexts` in the snapshot.
 * @param {number} [opts.tabCount] - If provided, included as `activeTabs` in the snapshot.
 * @returns {Object} An object with anonymized numeric metrics (missing or unavailable values are `null`).
 * @property {number} nodeRssMb - Rounded MB of Node's RSS.
 * @property {number} nodeHeapUsedMb - Rounded MB of Node's heap used.
 * @property {number} nodeHeapTotalMb - Rounded MB of Node's heap total.
 * @property {number} nodeExternalMb - Rounded MB of Node's external memory.
 * @property {number|null} eventLoopLagMs - Placeholder for event-loop lag in milliseconds (currently `null`).
 * @property {number|null} activeHandles - Count of active libuv handles if available, otherwise `null`.
 * @property {number|null} activeRequests - Count of active libuv requests if available, otherwise `null`.
 * @property {number|null} openFds - Count of open file descriptors on Linux if accessible, otherwise `null`.
 * @property {number|null} browserRssMb - Rounded MB of the browser process RSS when `opts.browserPid` is provided and accessible, otherwise `null`.
 * @property {number|undefined} browserContexts - Caller-provided session count when `opts.sessionCount` is supplied.
 * @property {number|undefined} activeTabs - Caller-provided tab count when `opts.tabCount` is supplied.
 */
export function collectResourceSnapshot(opts = {}) {
  const mem = process.memoryUsage();
  const snap = {
    nodeRssMb: Math.round(mem.rss / 1048576),
    nodeHeapUsedMb: Math.round(mem.heapUsed / 1048576),
    nodeHeapTotalMb: Math.round(mem.heapTotal / 1048576),
    nodeExternalMb: Math.round(mem.external / 1048576),
    eventLoopLagMs: null,
    activeHandles: null,
    activeRequests: null,
    openFds: null,
    browserRssMb: null,
  };

  // Active libuv handles/requests (private API, guarded)
  try {
    snap.activeHandles = process._getActiveHandles().length;
  } catch {
    /* unavailable */
  }
  try {
    snap.activeRequests = process._getActiveRequests().length;
  } catch {
    /* unavailable */
  }

  // Open file descriptors (Linux only)
  try {
    if (process.platform === 'linux') {
      snap.openFds = fs.readdirSync('/proc/self/fd').length;
    }
  } catch {
    /* not available or permission denied */
  }

  // Browser process RSS (the one people miss -- browser OOMs, not Node)
  if (
    opts.browserPid &&
    Number.isInteger(opts.browserPid) &&
    opts.browserPid > 0
  ) {
    try {
      if (process.platform === 'linux') {
        const status = fs.readFileSync(
          `/proc/${opts.browserPid}/status`,
          'utf8',
        );
        const match = status.match(/VmRSS:\s+(\d+)\s+kB/);
        if (match)
          snap.browserRssMb = Math.round(parseInt(match[1], 10) / 1024);
      }
    } catch {
      /* process gone or permission denied */
    }
  }

  // Session/tab counts from caller
  if (opts.sessionCount != null) snap.browserContexts = opts.sessionCount;
  if (opts.tabCount != null) snap.activeTabs = opts.tabCount;

  return snap;
}

// ============================================================================
// Proxy error classification
// ============================================================================

/**
 * Determines proxy-related classification from a navigation or network error message.
 * @param {string} errorMessage - Error message text to classify; may be null or non-string.
 * @returns {{proxyError: string|null, proxyTlsError: boolean}} `proxyError` is one of
 * `'ERR_PROXY_CONNECTION_FAILED'`, `'ERR_TUNNEL_CONNECTION_FAILED'`, `'ERR_PROXY_AUTH_REQUESTED'`,
 * `'ERR_PROXY_TLS'`, `'ECONNREFUSED'`, `'ETIMEDOUT'`, or `null` when no proxy pattern is detected.
 * `proxyTlsError` is `true` when the failure indicates a proxy TLS/certificate issue, otherwise `false`.
 */
export function classifyProxyError(errorMessage) {
  if (!errorMessage || typeof errorMessage !== 'string')
    return { proxyError: null, proxyTlsError: false };
  const msg = errorMessage.toUpperCase();
  if (msg.includes('ERR_PROXY_CONNECTION_FAILED'))
    return { proxyError: 'ERR_PROXY_CONNECTION_FAILED', proxyTlsError: false };
  if (msg.includes('ERR_TUNNEL_CONNECTION_FAILED'))
    return { proxyError: 'ERR_TUNNEL_CONNECTION_FAILED', proxyTlsError: false };
  if (msg.includes('ERR_PROXY_AUTH_REQUESTED') || msg.includes('407'))
    return { proxyError: 'ERR_PROXY_AUTH_REQUESTED', proxyTlsError: false };
  if (
    msg.includes('ERR_PROXY_CERTIFICATE_INVALID') ||
    (msg.includes('PROXY') && msg.includes('SSL'))
  )
    return { proxyError: 'ERR_PROXY_TLS', proxyTlsError: true };
  if (msg.includes('ECONNREFUSED') && msg.includes('PROXY'))
    return { proxyError: 'ECONNREFUSED', proxyTlsError: false };
  if (msg.includes('ETIMEDOUT') && msg.includes('PROXY'))
    return { proxyError: 'ETIMEDOUT', proxyTlsError: false };
  return { proxyError: null, proxyTlsError: false };
}
