import { launchOptions } from 'camoufox-js';
import { VirtualDisplay } from 'camoufox-js/dist/virtdisplay.js';
import express from 'express';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import { firefox } from 'playwright-core';
import {
  isLoopbackAddress as _isLoopbackAddress,
  timingSafeCompare as _timingSafeCompare,
  accessKeyMiddleware,
  requireAuth,
} from './lib/auth.js';
import { loadConfig } from './lib/config.js';
import {
  attachDownloadListener,
  clearSessionDownloads,
  clearTabDownloads,
} from './lib/downloads.js';
import { createFlyHelpers } from './lib/fly.js';
import { expandMacro } from './lib/macros.js';
import { createPluginEvents, loadPlugins } from './lib/plugins.js';
import {
  buildProxyUrl,
  createProxyPool,
  normalizePlaywrightProxy,
} from './lib/proxy.js';
import {
  INTERACTIVE_ROLES,
  SKIP_PATTERNS,
  StaleRefsError,
  createRefHelpers,
} from './lib/refs.js';
import { createGoogleSerpHelpers } from './lib/google-serp.js';
import { windowSnapshot } from './lib/snapshot.js';
import {
  ensureTracesDir,
  makeTraceFilename,
  sweepOldTraces,
  tracePathFor,
} from './lib/tracing.js';

import { coalesceInflight } from './lib/inflight.js';
import {
  createMetric,
  getRegister,
  initMetrics,
  startMemoryReporter,
  stopMemoryReporter,
} from './lib/metrics.js';
import { mountDocs } from './lib/openapi.js';
import { mountLegacyActionRoutes } from './lib/routes/legacy-actions.js';
import { mountLegacyCoreRoutes } from './lib/routes/legacy-core.js';
import { mountSessionRoutes } from './lib/routes/sessions.js';
import { mountSystemRoutes } from './lib/routes/system.js';
import { mountTabClickRoutes } from './lib/routes/tabs-click.js';
import { mountTabContentRoutes } from './lib/routes/tabs-content.js';
import { mountTabEvaluationRoutes } from './lib/routes/tabs-evaluation.js';
import { mountTabHistoryRoutes } from './lib/routes/tabs-history.js';
import { mountTabInteractionRoutes } from './lib/routes/tabs-interaction.js';
import { mountTabLifecycleRoutes } from './lib/routes/tabs-lifecycle.js';
import { mountTabNavigationRoutes } from './lib/routes/tabs-navigation.js';
import { mountTabSnapshotRoutes } from './lib/routes/tabs-snapshot.js';
import { mountTabTypingRoutes } from './lib/routes/tabs-typing.js';
import { mountTraceRoutes } from './lib/routes/traces.js';
import { mountLegacySnapshotRoutes } from './lib/routes/legacy-snapshot.js';
import {
  classifyProxyError,
  createReporter,
  createTabHealthTracker,
} from './lib/reporter.js';
import { actionFromReq, classifyError } from './lib/request-utils.js';
import {
  cleanupOrphanedTempFiles,
  cleanupStaleFirefoxProfiles,
} from './lib/tmp-cleanup.js';

const CONFIG = loadConfig();

// --- Local reporter facade (no external telemetry in Agentic Trader) ---
const _pkgVersion = (() => {
  try {
    return JSON.parse(
      fs.readFileSync(new URL('./package.json', import.meta.url), 'utf8'),
    ).version;
  } catch {
    return 'unknown';
  }
})();
const reporter = createReporter({ ...CONFIG, version: _pkgVersion });
function _countTabs() {
  let total = 0;
  for (const session of sessions.values()) {
    for (const group of session.tabGroups.values()) total += group.size;
  }
  return total;
}
function _browserPid() {
  try {
    return browser?.process?.()?.pid ?? null;
  } catch {
    return null;
  }
}
function _resourceOpts() {
  return {
    sessionCount: sessions.size,
    tabCount: _countTabs(),
    browserPid: _browserPid(),
  };
}
reporter.startWatchdog(30_000, () => {
  const summary = [];
  for (const [sid, session] of sessions) {
    const tabUrls = [];
    for (const [tid, tab] of session.tabs) {
      try {
        const url = tab.page?.url?.() || 'unknown';
        tabUrls.push(url);
      } catch {
        tabUrls.push('error');
      }
    }
    if (tabUrls.length > 0)
      summary.push({ session: sid, tabs: tabUrls.length, urls: tabUrls });
  }
  return { resourceOpts: _resourceOpts(), sessions: summary.length, summary };
});

// --- Plugin event bus ---
const pluginEvents = createPluginEvents();

// --- Shared auth middleware ---
const authMiddleware = () => requireAuth(CONFIG);
const {
  requestsTotal,
  requestDuration,
  pageLoadDuration,
  snapshotBytes,
  activeTabsGauge,
  tabLockQueueDepth,
  tabLockTimeoutsTotal,
  failuresTotal,
  browserRestartsTotal,
  tabsDestroyedTotal,
  sessionsExpiredTotal,
  tabsReapedTotal,
  tabsRecycledTotal,
} = await initMetrics({ enabled: CONFIG.prometheusEnabled });

// --- Structured logging ---
function log(level, msg, fields = {}) {
  const entry = {
    ts: new Date().toISOString(),
    level,
    msg,
    ...fields,
  };
  const line = JSON.stringify(entry);
  if (level === 'error') {
    process.stderr.write(line + '\n');
  } else {
    process.stdout.write(line + '\n');
  }
}

const {
  extractGoogleSerp,
  isGoogleSearchBlocked,
  isGoogleSearchUrl,
  isGoogleSerp,
} = createGoogleSerpHelpers({ log });

const app = express();
app.use(express.json({ limit: '100kb' }));

// Request logging + metrics middleware
app.use((req, res, next) => {
  const reqId = crypto.randomUUID().slice(0, 8);
  req.reqId = reqId;
  req.startTime = Date.now();

  const userId = req.body?.userId || req.query?.userId || '-';
  if (req.path !== '/health') {
    log('info', 'req', { reqId, method: req.method, path: req.path, userId });
  }

  const action = actionFromReq(req);
  reporter.trackRoute(`${req.method} ${req.route?.path || '[unmatched]'}`);
  const done = requestDuration.startTimer({ action });

  const origEnd = res.end.bind(res);
  res.end = function (...args) {
    const ms = Date.now() - req.startTime;
    const isErrorStatus = res.statusCode >= 400;
    requestsTotal.labels(action, isErrorStatus ? 'error' : 'success').inc();
    done();

    if (req.path !== '/health') {
      log('info', 'res', { reqId, status: res.statusCode, ms });
    }

    return origEnd(...args);
  };

  next();
});

// --- Horizontal scaling (Fly.io multi-machine) ---
const fly = createFlyHelpers(CONFIG);
const FLY_MACHINE_ID = fly.machineId;

// Route tab requests to the owning machine via fly-replay header.
app.use('/tabs/:tabId', fly.replayMiddleware(log));

// Access-key middleware: gates every route when CAMOFOX_ACCESS_KEY is set.
// Exempts /health (Docker healthcheck) and routes that have their own
// dedicated keys (cookie import -> CAMOFOX_API_KEY, /stop -> CAMOFOX_ADMIN_KEY)
// so each key gates a distinct surface. When unset, behavior is unchanged.
app.use(accessKeyMiddleware(CONFIG));

const ALLOWED_URL_SCHEMES = ['http:', 'https:'];

// timingSafeCompare imported from lib/auth.js
const timingSafeCompare = _timingSafeCompare;

function safeError(err) {
  if (CONFIG.nodeEnv === 'production') {
    log('error', 'internal error', { error: err.message, stack: err.stack });
    return 'Internal server error';
  }
  return err.message;
}

// Send error response with appropriate status code (422 for stale refs, 500 otherwise)
function sendError(res, err, extraFields = {}) {
  const status = err instanceof StaleRefsError ? 422 : err.statusCode || 500;
  const body = { error: safeError(err), ...extraFields };
  if (err instanceof StaleRefsError) {
    body.code = 'stale_refs';
    body.ref = err.ref;
  }
  res.status(status).json(body);
}

function validateUrl(url) {
  try {
    const parsed = new URL(url);
    if (!ALLOWED_URL_SCHEMES.includes(parsed.protocol)) {
      return `Blocked URL scheme: ${parsed.protocol} (only http/https allowed)`;
    }
    return null;
  } catch {
    return `Invalid URL: ${url}`;
  }
}

let browser = null;
let _lastBrowserPid = null; // Track PID independently for force-kill after close
let _browserClosePromise = null; // Shared promise for concurrent close serialization
// userId -> { context, tabGroups: Map<sessionKey, Map<tabId, TabState>>, lastAccess }
// TabState = { page, refs: Map<refId, {role, name, nth}>, visitedUrls: Set, downloads: Array, toolCalls: number }
// Note: sessionKey was previously called listItemId - both are accepted for backward compatibility
const sessions = new Map();

const SESSION_TIMEOUT_MS = CONFIG.sessionTimeoutMs;
const MAX_SNAPSHOT_NODES = 500;
const TAB_INACTIVITY_MS = CONFIG.tabInactivityMs;
const MAX_SESSIONS = CONFIG.maxSessions;
const MAX_TABS_PER_SESSION = CONFIG.maxTabsPerSession;
const MAX_TABS_GLOBAL = CONFIG.maxTabsGlobal;
const HANDLER_TIMEOUT_MS = CONFIG.handlerTimeoutMs;
const MAX_CONCURRENT_PER_USER = CONFIG.maxConcurrentPerUser;
const PAGE_CLOSE_TIMEOUT_MS = 5000;
const NAVIGATE_TIMEOUT_MS = CONFIG.navigateTimeoutMs;
const BUILDREFS_TIMEOUT_MS = CONFIG.buildrefsTimeoutMs;
const NATIVE_MEM_RESTART_THRESHOLD_MB = CONFIG.nativeMemRestartThresholdMb;
let _nativeMemBaseline = null; // RSS - heapUsed at first idle measurement
const FAILURE_THRESHOLD = 3;
const MAX_CONSECUTIVE_TIMEOUTS = 3;
const TAB_LOCK_TIMEOUT_MS = 35000; // Must be > HANDLER_TIMEOUT_MS so active op times out first

const { buildRefs, getAriaSnapshot, refToLocator, refreshTabRefs } =
  createRefHelpers({
    buildrefsTimeoutMs: BUILDREFS_TIMEOUT_MS,
    extractGoogleSerp,
    isGoogleSerp,
    log,
    maxSnapshotNodes: MAX_SNAPSHOT_NODES,
    waitForPageReady,
  });

// Proper mutex for tab serialization. The old Promise-chain lock on timeout proceeded
// WITHOUT the lock, allowing concurrent Playwright operations that corrupt CDP state.
class TabLock {
  constructor() {
    this.queue = [];
    this.active = false;
  }

  acquire(timeoutMs) {
    return new Promise((resolve, reject) => {
      const entry = { resolve, reject, timer: null };
      entry.timer = setTimeout(() => {
        const idx = this.queue.indexOf(entry);
        if (idx !== -1) this.queue.splice(idx, 1);
        tabLockTimeoutsTotal.inc();
        refreshTabLockQueueDepth();
        reject(new Error('Tab lock queue timeout'));
      }, timeoutMs);
      this.queue.push(entry);
      refreshTabLockQueueDepth();
      this._tryNext();
    });
  }

  release() {
    this.active = false;
    this._tryNext();
    refreshTabLockQueueDepth();
  }

  _tryNext() {
    if (this.active || this.queue.length === 0) return;
    this.active = true;
    const entry = this.queue.shift();
    clearTimeout(entry.timer);
    refreshTabLockQueueDepth();
    entry.resolve();
  }

  drain() {
    this.active = true;
    for (const entry of this.queue) {
      clearTimeout(entry.timer);
      entry.reject(new Error('Tab destroyed'));
    }
    this.queue = [];
    refreshTabLockQueueDepth();
  }
}

// Per-tab locks to serialize operations on the same tab
const tabLocks = new Map(); // tabId -> TabLock

function getTabLock(tabId) {
  if (!tabLocks.has(tabId)) tabLocks.set(tabId, new TabLock());
  return tabLocks.get(tabId);
}

// Timeout is INSIDE the lock so each operation gets its full budget
// regardless of how long it waited in the queue.
async function withTabLock(tabId, operation, timeoutMs = HANDLER_TIMEOUT_MS) {
  const lock = getTabLock(tabId);
  await lock.acquire(TAB_LOCK_TIMEOUT_MS);
  try {
    return await withTimeout(operation(), timeoutMs, 'action');
  } finally {
    lock.release();
  }
}

function withTimeout(promise, ms, label) {
  return Promise.race([
    promise,
    new Promise((_, reject) =>
      setTimeout(
        () => reject(new Error(`${label} timed out after ${ms}ms`)),
        ms,
      ),
    ),
  ]);
}

function requestTimeoutMs(baseMs = HANDLER_TIMEOUT_MS) {
  return proxyPool?.canRotateSessions ? Math.max(baseMs, 180000) : baseMs;
}

const userConcurrency = new Map();

async function withUserLimit(userId, operation) {
  const key = normalizeUserId(userId);
  let state = userConcurrency.get(key);
  if (!state) {
    state = { active: 0, queue: [] };
    userConcurrency.set(key, state);
  }
  if (state.active >= MAX_CONCURRENT_PER_USER) {
    await new Promise((resolve, reject) => {
      const timer = setTimeout(
        () => reject(new Error('User concurrency limit reached, try again')),
        30000,
      );
      state.queue.push(() => {
        clearTimeout(timer);
        resolve();
      });
    });
  }
  state.active++;
  healthState.activeOps++;
  try {
    const result = await operation();
    healthState.lastSuccessfulNav = Date.now();
    return result;
  } finally {
    healthState.activeOps--;
    state.active--;
    if (state.queue.length > 0) {
      const next = state.queue.shift();
      next();
    }
    if (state.active === 0 && state.queue.length === 0) {
      userConcurrency.delete(key);
    }
  }
}

async function safePageClose(page) {
  try {
    await Promise.race([
      page.close(),
      new Promise((resolve) => setTimeout(resolve, PAGE_CLOSE_TIMEOUT_MS)),
    ]);
  } catch (e) {
    log('warn', 'page close failed', { error: e.message });
  }
}

// Detect host OS for fingerprint generation
function getHostOS() {
  const platform = os.platform();
  if (platform === 'darwin') return 'macos';
  if (platform === 'win32') return 'windows';
  return 'linux';
}

// Proxy strategy for outbound browsing.
const proxyPool = createProxyPool(CONFIG.proxy);

if (proxyPool) {
  log('info', 'proxy pool created', {
    mode: proxyPool.mode,
    host: proxyPool.canRotateSessions
      ? CONFIG.proxy.backconnectHost
      : CONFIG.proxy.host,
    ports: proxyPool.canRotateSessions
      ? [CONFIG.proxy.backconnectPort]
      : CONFIG.proxy.ports,
    poolSize: proxyPool.size,
    country: CONFIG.proxy.country || null,
    state: CONFIG.proxy.state || null,
    city: CONFIG.proxy.city || null,
  });
} else {
  log('info', 'no proxy configured');
}

const BROWSER_IDLE_TIMEOUT_MS = CONFIG.browserIdleTimeoutMs;
let browserIdleTimer = null;
let browserLaunchPromise = null;
let browserWarmRetryTimer = null;

function scheduleBrowserIdleShutdown() {
  clearBrowserIdleTimer();
  if (sessions.size === 0 && browser) {
    browserIdleTimer = setTimeout(async () => {
      if (sessions.size === 0 && browser) {
        log('info', 'browser idle shutdown (no sessions)');
        await closeBrowserFully('idle_shutdown');
      }
    }, BROWSER_IDLE_TIMEOUT_MS);
  }
}

function clearBrowserIdleTimer() {
  if (browserIdleTimer) {
    clearTimeout(browserIdleTimer);
    browserIdleTimer = null;
  }
}

function scheduleBrowserWarmRetry(delayMs = 5000) {
  if (!CONFIG.browserPrewarmEnabled) return;
  if (browserWarmRetryTimer || browser || browserLaunchPromise) return;
  browserWarmRetryTimer = setTimeout(async () => {
    browserWarmRetryTimer = null;
    try {
      const start = Date.now();
      await ensureBrowser();
      log('info', 'background browser warm retry succeeded', {
        ms: Date.now() - start,
      });
    } catch (err) {
      log('warn', 'background browser warm retry failed', {
        error: err.message,
        nextDelayMs: delayMs,
      });
      scheduleBrowserWarmRetry(Math.min(delayMs * 2, 30000));
    }
  }, delayMs);
}

// --- Browser health tracking ---
const healthState = {
  consecutiveNavFailures: 0,
  lastSuccessfulNav: Date.now(),
  isRecovering: false,
  activeOps: 0,
};

function recordNavSuccess() {
  healthState.consecutiveNavFailures = 0;
  healthState.lastSuccessfulNav = Date.now();
}

function recordNavFailure() {
  healthState.consecutiveNavFailures++;
  return healthState.consecutiveNavFailures >= FAILURE_THRESHOLD;
}

async function restartBrowser(reason) {
  if (healthState.isRecovering) return;
  healthState.isRecovering = true;
  browserRestartsTotal.labels(reason).inc();
  log('error', 'restarting browser', {
    reason,
    failures: healthState.consecutiveNavFailures,
  });
  pluginEvents.emit('browser:restart', { reason });
  try {
    await closeAllSessions(`browser_restart:${reason}`, {
      clearDownloads: true,
      clearLocks: true,
    });
    await closeBrowserFully(`browser_restart:${reason}`);
    pluginEvents.emit('browser:closed', { reason });
    browserLaunchPromise = null;
    await ensureBrowser();
    healthState.consecutiveNavFailures = 0;
    healthState.lastSuccessfulNav = Date.now();
    log('info', 'browser restarted successfully');
  } catch (err) {
    log('error', 'browser restart failed', { error: err.message });
  } finally {
    healthState.isRecovering = false;
  }
}

function getTotalTabCount() {
  let total = 0;
  for (const session of sessions.values()) {
    for (const group of session.tabGroups.values()) {
      total += group.size;
    }
  }
  return total;
}

// Virtual display for WebGL support and anti-detection.
// Xvfb gives Firefox a real X display with GLX, enabling software-rendered WebGL
// via Mesa llvmpipe. Without this, WebGL returns "no context" -- a massive bot signal.
let virtualDisplay = null;
let browserLaunchProxy = null;

async function probeGoogleSearch(candidateBrowser) {
  let context = null;
  try {
    context = await candidateBrowser.newContext({
      viewport: { width: 1280, height: 720 },
      permissions: ['geolocation'],
    });
    const page = await context.newPage();
    await page.goto('https://www.google.com/', {
      waitUntil: 'domcontentloaded',
      timeout: 30000,
    });
    await page.waitForTimeout(1200);
    await page.goto('https://www.google.com/search?q=weather%20today', {
      waitUntil: 'domcontentloaded',
      timeout: 30000,
    });
    await page.waitForTimeout(4000);

    const blocked = await isGoogleSearchBlocked(page);
    return {
      ok: !blocked && isGoogleSerp(page.url()),
      url: page.url(),
      blocked,
    };
  } finally {
    await context?.close().catch(() => {});
  }
}

function attachBrowserCleanup(candidateBrowser, localVirtualDisplay) {
  const origClose = candidateBrowser.close.bind(candidateBrowser);
  candidateBrowser.close = async (...args) => {
    await origClose(...args);
    browserLaunchProxy = null;
    if (localVirtualDisplay) {
      localVirtualDisplay.kill();
      if (virtualDisplay === localVirtualDisplay) virtualDisplay = null;
    }
  };
}

/**
 * Close browser with full process-tree cleanup. Handles the race where
 * browser.close() fails/hangs but process tree survives.
 *
 * Serialized: concurrent callers await the same promise (no double-close).
 *
 * Order: capture PID -> close browser -> force-kill survivors ->
 * clean temp profiles -> verify FD/handle drop.
 */
async function closeBrowserFully(reason) {
  if (_browserClosePromise) return _browserClosePromise;
  _browserClosePromise = _closeBrowserFullyImpl(reason);
  try {
    return await _browserClosePromise;
  } finally {
    _browserClosePromise = null;
  }
}

async function _closeBrowserFullyImpl(reason) {
  const b = browser;
  if (!b) return;

  // Capture PID before nulling browser ref -- we need it for force-kill
  const pid = _lastBrowserPid;
  const preCloseFds = _countOpenFds();
  const preCloseHandles = _countActiveHandles();

  // Null the ref so new requests don't use a dying browser
  browser = null;
  _lastBrowserPid = null;

  // Close through Playwright (sends CDP Browser.close, then SIGKILL process group)
  let closeTimer;
  try {
    await Promise.race([
      b.close(),
      new Promise((_, reject) => {
        closeTimer = setTimeout(
          () => reject(new Error('browser.close() timeout')),
          10000,
        );
      }),
    ]);
  } catch (err) {
    log('warn', 'browser.close() failed or timed out', {
      reason,
      error: err.message,
      pid,
    });
  } finally {
    clearTimeout(closeTimer);
  }

  // Force-kill the entire process tree if any survivors
  if (pid) {
    await _forceKillProcessTree(pid, reason);
  }

  // Clean up stale Firefox temp profiles (enable_cache: true accumulates data)
  try {
    const cleaned = cleanupStaleFirefoxProfiles();
    if (cleaned.removed > 0) {
      log(
        'info',
        'cleaned stale firefox profiles after browser close',
        cleaned,
      );
    }
  } catch {
    /* best effort */
  }

  // Reset native memory baseline so next browser measures from fresh
  reporter.resetNativeMemBaseline();
  _nativeMemBaseline = null;

  // Verify cleanup: check FD/handle counts dropped (after force-kill completes)
  const postCloseFds = _countOpenFds();
  const postCloseHandles = _countActiveHandles();
  if (postCloseFds !== null && preCloseFds !== null) {
    const fdDelta = postCloseFds - preCloseFds;
    // After close we expect fewer FDs. If more leaked, warn.
    if (fdDelta > 10) {
      log('warn', 'FD leak detected after browser close', {
        reason,
        preCloseFds,
        postCloseFds,
        delta: fdDelta,
        preCloseHandles,
        postCloseHandles,
      });
    }
  }
  log('info', 'browser closed fully', {
    reason,
    pid,
    preCloseFds,
    postCloseFds,
    preCloseHandles,
    postCloseHandles,
  });
}

/**
 * Force-kill a browser process tree by PID. On Linux, kills the process group
 * (SIGKILL -pid) then scans /proc for any orphaned children.
 */
async function _forceKillProcessTree(pid, reason) {
  if (!pid || pid <= 1) return;

  // Kill the specific browser process first (positive PID = single process)
  try {
    process.kill(pid, 'SIGKILL');
    log('info', 'sent SIGKILL to browser process', { pid, reason });
  } catch (err) {
    if (err.code !== 'ESRCH') {
      log('warn', 'failed to kill browser process', {
        pid,
        error: err.message,
      });
    }
  }

  // Then try the process group (Playwright launches with detached:true on Linux,
  // making the browser a process group leader)
  try {
    process.kill(-pid, 'SIGKILL');
  } catch {
    // ESRCH = group doesn't exist (browser wasn't a group leader), which is fine
  }

  // Wait for kernel to reparent children to PID 1 before scanning
  await new Promise((r) => setTimeout(r, 200));

  // On Linux: scan /proc for orphaned children that escaped the process group
  // (reparented to PID 1 by init/systemd, common with Firefox content processes).
  // Also checks PPid === Node PID for containerized environments without init.
  if (process.platform === 'linux') {
    const myPid = process.pid;
    // Snapshot the current browser PID to avoid killing a newly launched browser
    const currentBrowserPid = _lastBrowserPid;
    try {
      const procDirs = fs.readdirSync('/proc').filter((d) => /^\d+$/.test(d));
      const orphans = [];
      for (const procPid of procDirs) {
        const numPid = parseInt(procPid);
        // Never kill ourselves, the old PID (already killed), or the new browser
        if (numPid === myPid || numPid === pid || numPid === currentBrowserPid)
          continue;
        try {
          const status = fs.readFileSync(`/proc/${procPid}/status`, 'utf8');
          const ppidMatch = status.match(/PPid:\s+(\d+)/);
          const ppid = ppidMatch ? parseInt(ppidMatch[1]) : -1;
          // Orphaned to init (PID 1) or reparented to us (Node is PID 1 in containers)
          if (ppid === 1 || ppid === myPid) {
            const cmdline = fs.readFileSync(`/proc/${procPid}/cmdline`, 'utf8');
            // Firefox-specific: binary name or Gecko child process marker
            if (
              /firefox-esr|firefox|camoufox|libxul\.so|GeckoChildProcess/i.test(
                cmdline,
              )
            ) {
              orphans.push(numPid);
            }
          }
        } catch {
          /* process vanished or permission denied */
        }
      }
      if (orphans.length > 0) {
        log('warn', 'killing orphaned browser child processes', {
          orphans,
          reason,
        });
        for (const orphanPid of orphans) {
          try {
            process.kill(orphanPid, 'SIGKILL');
          } catch {
            /* already dead */
          }
        }
      }
    } catch (err) {
      log('warn', 'failed to scan for orphaned browser processes', {
        error: err.message,
      });
    }
  }

  // Give the OS a moment to reclaim resources
  await new Promise((r) => setTimeout(r, 300));
}

function _countOpenFds() {
  try {
    if (process.platform === 'linux')
      return fs.readdirSync('/proc/self/fd').length;
  } catch {
    /* unavailable */
  }
  return null;
}

function _countActiveHandles() {
  try {
    return process._getActiveHandles().length;
  } catch {
    return null;
  }
}

async function launchBrowserInstance() {
  const hostOS = getHostOS();
  const maxAttempts = proxyPool?.launchRetries ?? 1;
  let lastError = null;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    const launchProxy = proxyPool
      ? proxyPool.getLaunchProxy(
          proxyPool.canRotateSessions
            ? `browser-${crypto.randomUUID().replace(/-/g, '').slice(0, 12)}`
            : undefined,
        )
      : null;

    let localVirtualDisplay = null;
    let vdDisplay = undefined;
    let candidateBrowser = null;

    try {
      if (os.platform() === 'linux') {
        localVirtualDisplay = pluginCtx.createVirtualDisplay();
        vdDisplay = localVirtualDisplay.get();
        log('info', 'xvfb virtual display started', {
          display: vdDisplay,
          attempt,
        });
      }
    } catch (err) {
      log('warn', 'xvfb not available, falling back to headless', {
        error: err.message,
        attempt,
      });
      localVirtualDisplay = null;
    }

    const useVirtualDisplay = !!vdDisplay;
    log('info', 'launching camoufox', {
      hostOS,
      attempt,
      maxAttempts,
      geoip: !!launchProxy,
      proxyMode: proxyPool?.mode || null,
      proxyServer: launchProxy?.server || null,
      proxySession: launchProxy?.sessionId || null,
      proxyPoolSize: proxyPool?.size || 0,
      virtualDisplay: useVirtualDisplay,
    });

    try {
      const options = await launchOptions({
        headless: useVirtualDisplay ? false : true,
        os: hostOS,
        humanize: true,
        enable_cache: true,
        proxy: launchProxy,
        geoip: !!launchProxy,
        virtual_display: vdDisplay,
      });
      options.proxy = normalizePlaywrightProxy(options.proxy);
      await pluginEvents.emitAsync('browser:launching', { options });

      candidateBrowser = await firefox.launch(options);

      if (proxyPool?.canRotateSessions) {
        const probe = await probeGoogleSearch(candidateBrowser);
        if (!probe.ok) {
          log('warn', 'browser launch google probe failed', {
            attempt,
            maxAttempts,
            proxySession: launchProxy?.sessionId || null,
            url: probe.url,
          });
          if (attempt < maxAttempts) {
            await candidateBrowser.close().catch(() => {});
            if (localVirtualDisplay) localVirtualDisplay.kill();
            continue;
          }
          // Last attempt: accept browser in degraded mode rather than death-spiraling.
          // Non-Google sites will still work; Google requests will get blocked responses.
          log(
            'error',
            'all proxy sessions Google-blocked, accepting browser in degraded mode',
            {
              maxAttempts,
              proxySession: launchProxy?.sessionId || null,
            },
          );
        }
      }

      virtualDisplay = localVirtualDisplay;
      browserLaunchProxy = launchProxy;
      _lastBrowserPid = candidateBrowser.process?.()?.pid ?? null;
      browser = candidateBrowser; // publish AFTER PID is captured
      attachBrowserCleanup(browser, localVirtualDisplay);
      pluginEvents.emit('browser:launched', { browser, display: vdDisplay });

      log('info', 'camoufox launched', {
        attempt,
        maxAttempts,
        virtualDisplay: useVirtualDisplay,
        proxyMode: proxyPool?.mode || null,
        proxyServer: launchProxy?.server || null,
        proxySession: launchProxy?.sessionId || null,
      });
      return browser;
    } catch (err) {
      lastError = err;
      log('warn', 'camoufox launch attempt failed', {
        attempt,
        maxAttempts,
        error: err.message,
        proxySession: launchProxy?.sessionId || null,
      });
      await candidateBrowser?.close().catch(() => {});
      if (localVirtualDisplay) localVirtualDisplay.kill();
    }
  }

  throw lastError || new Error('Failed to launch a usable browser');
}

async function ensureBrowser() {
  clearBrowserIdleTimer();
  if (browser && !browser.isConnected()) {
    failuresTotal.labels('browser_disconnected', 'internal').inc();
    log(
      'warn',
      'browser disconnected, clearing dead sessions and relaunching',
      {
        deadSessions: sessions.size,
      },
    );
    await closeAllSessions('browser_disconnected', {
      clearDownloads: true,
      clearLocks: true,
    });
    await closeBrowserFully('browser_disconnected');
  }
  if (browser) return browser;
  if (browserLaunchPromise) return browserLaunchPromise;
  const launchTimeoutMs = proxyPool?.launchTimeoutMs ?? 60000;
  browserLaunchPromise = Promise.race([
    launchBrowserInstance(),
    new Promise((_, reject) =>
      setTimeout(
        () =>
          reject(
            new Error(
              `Browser launch timeout (${Math.round(launchTimeoutMs / 1000)}s)`,
            ),
          ),
        launchTimeoutMs,
      ),
    ),
  ]).finally(() => {
    browserLaunchPromise = null;
  });
  return browserLaunchPromise;
}

// Helper to normalize userId to string (JSON body may parse as number)
function normalizeUserId(userId) {
  return String(userId);
}

const sessionCreations = new Map();

function clearSessionLocks(session) {
  if (!session?.tabGroups) return;
  for (const [, group] of session.tabGroups) {
    for (const tabId of group.keys()) {
      const lock = tabLocks.get(tabId);
      if (lock) {
        lock.drain();
        tabLocks.delete(tabId);
      }
    }
  }
  refreshTabLockQueueDepth();
}

async function closeSession(
  userId,
  session,
  { reason = 'session_closed', clearDownloads = true, clearLocks = true } = {},
) {
  if (!session) return;

  const key = normalizeUserId(userId);

  if (clearDownloads) {
    await clearSessionDownloads(session).catch(() => {});
  }

  await pluginEvents.emitAsync('session:destroying', { userId: key, reason });
  if (session.tracePath) {
    try {
      await session.context.tracing.stop({ path: session.tracePath });
      log('info', 'tracing saved', { userId: key, path: session.tracePath });
    } catch (err) {
      log('warn', 'tracing.stop failed', { userId: key, error: err.message });
    }
  }

  await session.context.close().catch(() => {});
  sessions.delete(key);
  await pluginEvents.emitAsync('session:destroyed', { userId: key, reason });

  if (clearLocks) {
    clearSessionLocks(session);
  }

  refreshActiveTabsGauge();
}

async function closeAllSessions(
  reason,
  { clearDownloads = true, clearLocks = true } = {},
) {
  const openSessions = Array.from(sessions.entries());
  for (const [userId, session] of openSessions) {
    await closeSession(userId, session, { reason, clearDownloads, clearLocks });
  }
}

/**
 * Return an active session for the given user, creating a new Playwright context if none exists or the existing context is dead.
 *
 * @param {string} userId - Identifier for the user; coerced to a normalized session key.
 * @param {Object} [options]
 * @param {boolean} [options.trace=false] - When true, enable tracing for the created session (saved to the configured traces directory) if supported.
 * @returns {{ context: import('playwright').BrowserContext, tabGroups: Map, lastAccess: number, proxySessionId: string|null, tracePath: string|null }} The session object containing the Playwright context, tab group map, last access timestamp, optional proxy session id, and optional trace path.
 * @throws {Error} If the maximum number of concurrent sessions has been reached.
 */
async function getSession(userId, { trace = false } = {}) {
  const key = normalizeUserId(userId);
  let session = sessions.get(key);

  // Check if existing session's context is still alive
  if (session) {
    if (session._closing) {
      // Session is being torn down by reaper/expiry -- treat as dead
      session = null;
    } else {
      try {
        // Lightweight probe: pages() is synchronous-ish and throws if context is dead
        session.context.pages();
      } catch (err) {
        log('warn', 'session context dead, recreating', {
          userId: key,
          error: err.message,
        });
        await closeSession(key, session, {
          reason: 'dead_context',
          clearDownloads: true,
          clearLocks: true,
        });
        session = null;
      }
    }
  }

  if (!session) {
    session = await coalesceInflight(sessionCreations, key, async () => {
      if (sessions.size >= MAX_SESSIONS) {
        throw new Error('Maximum concurrent sessions reached');
      }
      const b = await ensureBrowser();
      const contextOptions = {
        viewport: { width: 1280, height: 720 },
        permissions: ['geolocation'],
      };
      // When geoip is active (proxy configured), camoufox auto-configures
      // locale/timezone/geolocation from the proxy IP. Without proxy, use defaults.
      if (!CONFIG.proxy.host) {
        contextOptions.locale = 'en-US';
        contextOptions.timezoneId = 'America/Los_Angeles';
        contextOptions.geolocation = {
          latitude: 37.7749,
          longitude: -122.4194,
        };
      }
      let sessionProxy = null;
      if (proxyPool?.canRotateSessions) {
        sessionProxy = proxyPool.getNext(
          `ctx-${key}-${crypto.randomUUID().replaceAll('-', '').slice(0, 8)}`,
        );
        contextOptions.proxy = normalizePlaywrightProxy(sessionProxy);
        log('info', 'session proxy assigned', {
          userId: key,
          sessionId: sessionProxy.sessionId,
        });
      } else if (proxyPool) {
        sessionProxy = proxyPool.getNext();
        contextOptions.proxy = normalizePlaywrightProxy(sessionProxy);
        log('info', 'session proxy assigned', {
          userId: key,
          proxy: sessionProxy.server,
        });
      }
      await pluginEvents.emitAsync('session:creating', {
        userId: key,
        contextOptions,
      });
      const context = await b.newContext(contextOptions);

      let tracePath = null;
      if (trace) {
        const traceDir = ensureTracesDir(CONFIG.tracesDir, key);
        tracePath = tracePathFor(CONFIG.tracesDir, key, makeTraceFilename());
        try {
          await context.tracing.start({
            screenshots: true,
            snapshots: true,
            sources: false,
          });
          log('info', 'tracing enabled for session', {
            userId: key,
            traceDir,
            tracePath,
          });
        } catch (err) {
          log('warn', 'tracing.start failed; session will not be traced', {
            userId: key,
            error: err.message,
          });
          tracePath = null;
        }
      }

      const created = {
        context,
        tabGroups: new Map(),
        lastAccess: Date.now(),
        proxySessionId: sessionProxy?.sessionId || null,
        tracePath,
      };
      sessions.set(key, created);
      await pluginEvents.emitAsync('session:created', { userId: key, context });
      log('info', 'session created', {
        userId: key,
        proxyMode: proxyPool?.mode || null,
        proxyServer: sessionProxy?.server || browserLaunchProxy?.server || null,
        proxySession:
          sessionProxy?.sessionId || browserLaunchProxy?.sessionId || null,
      });
      return created;
    });
  }
  session.lastAccess = Date.now();
  return session;
}

/**
 * Return the tab group Map for the given group key, creating and storing a new Map if none exists.
 * @param {Object} session - Session object that contains `tabGroups`.
 * @param {string} listItemId - Group key (sessionKey or legacy listItemId).
 * @returns {Map<string, Object>} Map from `tabId` to `TabState` for the specified group.
 */
function getTabGroup(session, listItemId) {
  let group = session.tabGroups.get(listItemId);
  if (!group) {
    group = new Map();
    session.tabGroups.set(listItemId, group);
  }
  return group;
}

/**
 * Determines whether an error indicates a closed Playwright page, context, or browser.
 * @param {*} err - Error object or value; its `message` property will be inspected if present.
 * @returns {boolean} `true` if the error message reports a closed page, context, or browser, `false` otherwise.
 */
function isDeadContextError(err) {
  const msg = err?.message || '';
  return (
    msg.includes('Target page, context or browser has been closed') ||
    msg.includes('browser has been closed') ||
    msg.includes('Context closed') ||
    msg.includes('Browser closed')
  );
}

/**
 * Detects whether an error represents a timeout by inspecting its message text.
 * @param {any} err - An error-like value; its `message` property (if present) will be examined.
 * @returns {boolean} `true` if the error message indicates a timeout, `false` otherwise.
 */
function isTimeoutError(err) {
  const msg = err?.message || '';
  return (
    msg.includes('timed out after') ||
    (msg.includes('Timeout') && msg.includes('exceeded'))
  );
}

/**
 * Determines whether an error represents a tab lock queue timeout.
 * @param {Error|any} err - The error object to inspect.
 * @returns {boolean} `true` if the error's message equals "Tab lock queue timeout", `false` otherwise.
 */
function isTabLockQueueTimeout(err) {
  return err?.message === 'Tab lock queue timeout';
}

/**
 * Determines whether an error indicates that a tab was destroyed.
 * @param {any} err - Error object or value to inspect.
 * @returns {boolean} `true` if the error message is exactly `'Tab destroyed'`, `false` otherwise.
 */
function isTabDestroyedError(err) {
  return err?.message === 'Tab destroyed';
}

// Centralized error handler for route catch blocks.
// Auto-destroys dead browser sessions and returns appropriate status codes.
function isProxyError(err) {
  if (!err) return false;
  const msg = err.message || '';
  return (
    msg.includes('NS_ERROR_PROXY') ||
    msg.includes('proxy connection') ||
    msg.includes('Proxy connection')
  );
}

function handleRouteError(err, req, res, extraFields = {}) {
  const failureType = classifyError(err);
  const action = actionFromReq(req);
  failuresTotal.labels(failureType, action).inc();

  const userId = req.body?.userId || req.query?.userId;
  const tabId = req.body?.tabId || req.query?.tabId || req.params?.tabId;
  if (tabId) {
    pluginEvents.emit('tab:error', { userId, tabId, error: err });
  }
  if (userId && isDeadContextError(err)) {
    destroySession(userId);
  }
  // Proxy errors mean the session is dead -- rotate at context level.
  // Destroy the user's session so the next request gets a fresh context with a new proxy.
  if (isProxyError(err) && proxyPool?.canRotateSessions && userId) {
    log(
      'warn',
      'proxy error detected, destroying user session for fresh proxy on next request',
      {
        action,
        userId,
        error: err.message,
      },
    );
    browserRestartsTotal.labels('proxy_error').inc();
    destroySession(userId);
  }
  // Track consecutive timeouts per tab and auto-destroy stuck tabs
  if (userId && isTimeoutError(err)) {
    const tabId = req.body?.tabId || req.query?.tabId || req.params?.tabId;
    const session = sessions.get(normalizeUserId(userId));
    if (session && tabId) {
      const found = findTab(session, tabId);
      if (found) {
        found.tabState.consecutiveTimeouts++;
        if (found.tabState.consecutiveTimeouts >= MAX_CONSECUTIVE_TIMEOUTS) {
          log('warn', 'auto-destroying tab after consecutive timeouts', {
            tabId,
            count: found.tabState.consecutiveTimeouts,
          });
          destroyTab(session, tabId, 'consecutive_timeouts', userId);
        }
      }
    }
  }
  // Lock queue timeout = tab is stuck. Destroy immediately.
  if (userId && isTabLockQueueTimeout(err)) {
    const session = sessions.get(normalizeUserId(userId));
    if (session && tabId) {
      destroyTab(session, tabId, 'lock_queue', userId);
    }
    return res.status(503).json({
      error: 'Tab unresponsive and has been destroyed. Open a new tab.',
      ...extraFields,
    });
  }
  // Tab was destroyed while this request was queued in the lock
  if (isTabDestroyedError(err)) {
    return res
      .status(410)
      .json({ error: 'Tab was destroyed. Open a new tab.', ...extraFields });
  }
  // --- Frustration detection: report when a tab hits a streak of failures ---
  // Individual failures are noise. 3+ consecutive = the site is persistently broken.
  const FRUSTRATION_TYPES = new Set(['timeout', 'dead_context', 'nav_aborted']);
  if (FRUSTRATION_TYPES.has(failureType) && userId && tabId) {
    const session = sessions.get(normalizeUserId(userId));
    const found = session && findTab(session, tabId);
    if (found) {
      const ts = found.tabState;
      ts.consecutiveFailures = (ts.consecutiveFailures || 0) + 1;
      if (!ts.failureJournal) ts.failureJournal = [];
      ts.failureJournal.push({ type: failureType, action, at: Date.now() });
      if (ts.failureJournal.length > 20)
        ts.failureJournal = ts.failureJournal.slice(-20);

      if (ts.consecutiveFailures === 3) {
        const _proxyErr = classifyProxyError(err?.message);
        reporter.reportHang(
          action,
          req.startTime ? Date.now() - req.startTime : 0,
          {
            error: err,
            healthSnapshot: ts.healthTracker
              ? ts.healthTracker.snapshot()
              : undefined,
            healthTracker: ts.healthTracker || null,
            resourceOpts: _resourceOpts(),
            proxy: proxyPool
              ? {
                  configured: true,
                  type: proxyPool.mode || null,
                  authConfigured: !!CONFIG.proxy?.username,
                  error: _proxyErr.proxyError,
                  tlsError: _proxyErr.proxyTlsError,
                }
              : { configured: false },
            context: {
              failureType,
              consecutiveFailures: ts.consecutiveFailures,
              toolCalls: ts.toolCalls,
              journal: ts.failureJournal.map((j) => `${j.type}:${j.action}`),
            },
          },
        );
      }
    }
  }
  sendError(res, err, extraFields);
}

function destroyTab(session, tabId, reason, userId) {
  const lock = tabLocks.get(tabId);
  if (lock) {
    lock.drain();
    tabLocks.delete(tabId);
    refreshTabLockQueueDepth();
  }
  for (const [listItemId, group] of session.tabGroups) {
    if (group.has(tabId)) {
      const tabState = group.get(tabId);
      log('warn', 'destroying stuck tab', {
        tabId,
        listItemId,
        toolCalls: tabState.toolCalls,
        reason: reason || 'unknown',
      });
      safePageClose(tabState.page);
      group.delete(tabId);
      if (group.size === 0) session.tabGroups.delete(listItemId);
      refreshActiveTabsGauge();
      if (reason) tabsDestroyedTotal.labels(reason).inc();
      pluginEvents.emit('tab:destroyed', {
        userId: userId || null,
        tabId,
        reason: reason || 'unknown',
      });
      return true;
    }
  }
  return false;
}

/**
 * Recycle the oldest (least-used) tab in a session to free a slot.
 * Closes the old tab's page and removes it from its group.
 * Returns { recycledTabId, recycledFromGroup } or null if no tab to recycle.
 */
async function recycleOldestTab(session, reqId, userId) {
  let oldestTab = null;
  let oldestGroup = null;
  let oldestGroupKey = null;
  let oldestTabId = null;
  for (const [gKey, group] of session.tabGroups) {
    for (const [tid, ts] of group) {
      if (!oldestTab || ts.toolCalls < oldestTab.toolCalls) {
        oldestTab = ts;
        oldestGroup = group;
        oldestGroupKey = gKey;
        oldestTabId = tid;
      }
    }
  }
  if (!oldestTab) return null;

  await safePageClose(oldestTab.page);
  oldestGroup.delete(oldestTabId);
  if (oldestGroup.size === 0) session.tabGroups.delete(oldestGroupKey);
  const lock = tabLocks.get(oldestTabId);
  if (lock) {
    lock.drain();
    tabLocks.delete(oldestTabId);
  }
  refreshTabLockQueueDepth();
  tabsRecycledTotal.inc();
  pluginEvents.emit('tab:recycled', {
    userId: userId || null,
    tabId: oldestTabId,
  });
  log('info', 'tab recycled (limit reached)', {
    reqId,
    recycledTabId: oldestTabId,
    recycledFromGroup: oldestGroupKey,
  });
  return { recycledTabId: oldestTabId, recycledFromGroup: oldestGroupKey };
}

function destroySession(userId) {
  const key = normalizeUserId(userId);
  const session = sessions.get(key);
  if (!session) return;
  log('warn', 'destroying dead session', { userId: key });
  sessions.delete(key);
  closeSession(key, session, {
    reason: 'destroy_session',
    clearDownloads: true,
    clearLocks: true,
  }).catch(() => {});
}

function findTab(session, tabId) {
  for (const [listItemId, group] of session.tabGroups) {
    if (group.has(tabId)) {
      const tabState = group.get(tabId);
      return { tabState, listItemId, group };
    }
  }
  return null;
}

function createTabState(page) {
  const healthTracker = createTabHealthTracker(page);
  return {
    page,
    refs: new Map(),
    visitedUrls: new Set(),
    downloads: [],
    toolCalls: 0,
    consecutiveTimeouts: 0,
    consecutiveFailures: 0,
    failureJournal: [],
    healthTracker,
    lastSnapshot: null,
    lastRequestedUrl: null,
    googleRetryCount: 0,
    navigateAbort: null,
  };
}

async function isGoogleUnavailable(page) {
  if (!page || page.isClosed()) return false;
  const bodyText = await page
    .evaluate(() => document.body?.innerText?.slice(0, 600) || '')
    .catch(() => '');
  return /Unable to connect|502 Bad Gateway or Proxy Error|Camoufox can't establish a connection/.test(
    bodyText,
  );
}

async function rotateGoogleTab(
  userId,
  sessionKey,
  tabId,
  previousTabState,
  reason,
  reqId,
) {
  if (
    !previousTabState?.lastRequestedUrl ||
    !isGoogleSearchUrl(previousTabState.lastRequestedUrl)
  )
    return null;
  if ((previousTabState.googleRetryCount || 0) >= 3) return null;

  browserRestartsTotal.labels(reason).inc(); // track rotation events (not a full restart)

  // Rotate at context level -- create a fresh context with a new proxy session
  // instead of restarting the entire browser (which kills ALL sessions/tabs).
  const key = normalizeUserId(userId);
  const oldSession = sessions.get(key);
  if (oldSession) {
    await closeSession(key, oldSession, {
      reason: 'google_rotate_context',
      clearDownloads: true,
      clearLocks: true,
    });
  }
  const session = await getSession(userId);
  const group = getTabGroup(session, sessionKey);
  const page = await session.context.newPage();
  const tabState = createTabState(page);
  tabState.googleRetryCount = (previousTabState.googleRetryCount || 0) + 1;
  tabState.lastRequestedUrl = previousTabState.lastRequestedUrl;
  attachDownloadListener(tabState, tabId, log, pluginEvents, userId);
  group.set(tabId, tabState);
  refreshActiveTabsGauge();

  log(
    'warn',
    'replaying google search on fresh context (per-context proxy rotation)',
    {
      reqId,
      tabId,
      retryCount: tabState.googleRetryCount,
      url: tabState.lastRequestedUrl,
      proxySession: session.proxySessionId || null,
    },
  );

  await withPageLoadDuration('navigate', () =>
    page.goto('https://www.google.com/', {
      waitUntil: 'domcontentloaded',
      timeout: 30000,
    }),
  );
  tabState.visitedUrls.add('https://www.google.com/');
  await page.waitForTimeout(1200);
  await withPageLoadDuration('navigate', () =>
    page.goto(tabState.lastRequestedUrl, {
      waitUntil: 'domcontentloaded',
      timeout: 30000,
    }),
  );
  tabState.visitedUrls.add(tabState.lastRequestedUrl);
  return { session, tabState };
}

function refreshActiveTabsGauge() {
  activeTabsGauge.set(getTotalTabCount());
}

function refreshTabLockQueueDepth() {
  let queued = 0;
  for (const lock of tabLocks.values()) {
    if (lock?.queue) queued += lock.queue.length;
  }
  tabLockQueueDepth.set(queued);
}

async function withPageLoadDuration(action, fn) {
  const end = pageLoadDuration.startTimer();
  try {
    return await fn();
  } finally {
    end();
  }
}

async function waitForPageReady(page, options = {}) {
  const {
    timeout = 10000,
    waitForNetwork = true,
    waitForHydration = true,
    settleMs = 200,
    hydrationPollMs = 250,
    hydrationTimeoutMs = Math.min(timeout, 10000),
  } = options;

  try {
    await page.waitForLoadState('domcontentloaded', { timeout });

    if (waitForNetwork) {
      await page
        .waitForLoadState('networkidle', { timeout: 5000 })
        .catch(() => {
          log('warn', 'networkidle timeout, continuing');
        });
    }

    if (waitForHydration) {
      const maxIterations = Math.max(
        1,
        Math.floor(hydrationTimeoutMs / hydrationPollMs),
      );
      await page
        .evaluate(
          async ({ maxIterations, hydrationPollMs }) => {
            for (let i = 0; i < maxIterations; i++) {
              const entries = performance.getEntriesByType('resource');
              const recentEntries = entries.slice(-5);
              const netQuiet = recentEntries.every(
                (e) => performance.now() - e.responseEnd > 400,
              );

              if (document.readyState === 'complete' && netQuiet) {
                await new Promise((r) =>
                  requestAnimationFrame(() => requestAnimationFrame(r)),
                );
                break;
              }
              await new Promise((r) => setTimeout(r, hydrationPollMs));
            }
          },
          { maxIterations, hydrationPollMs },
        )
        .catch(() => {
          log('warn', 'hydration wait failed, continuing');
        });
    }

    if (settleMs > 0) {
      await page.waitForTimeout(settleMs);
    }

    // Auto-dismiss common consent/privacy dialogs
    await dismissConsentDialogs(page);

    return true;
  } catch (err) {
    log('warn', 'page ready failed', { error: err.message });
    return false;
  }
}

async function dismissConsentDialogs(page) {
  // Common consent/privacy dialog selectors (matches Swift WebView.swift patterns)
  const dismissSelectors = [
    // OneTrust (very common)
    '#onetrust-banner-sdk button#onetrust-accept-btn-handler',
    '#onetrust-banner-sdk button#onetrust-reject-all-handler',
    '#onetrust-close-btn-container button',
    // Generic patterns
    'button[data-test="cookie-accept-all"]',
    'button[aria-label="Accept all"]',
    'button[aria-label="Accept All"]',
    'button[aria-label="Close"]',
    'button[aria-label="Dismiss"]',
    // Dialog close buttons
    'dialog button:has-text("Close")',
    'dialog button:has-text("Accept")',
    'dialog button:has-text("I Accept")',
    'dialog button:has-text("Got it")',
    'dialog button:has-text("OK")',
    // GDPR/CCPA specific
    '[class*="consent"] button[class*="accept"]',
    '[class*="consent"] button[class*="close"]',
    '[class*="privacy"] button[class*="close"]',
    '[class*="cookie"] button[class*="accept"]',
    '[class*="cookie"] button[class*="close"]',
    // Overlay close buttons
    '[class*="modal"] button[class*="close"]',
    '[class*="overlay"] button[class*="close"]',
  ];

  for (const selector of dismissSelectors) {
    try {
      const button = page.locator(selector).first();
      if (await button.isVisible({ timeout: 100 })) {
        await button.click({ timeout: 1000 }).catch(() => {});
        log('info', 'dismissed consent dialog', { selector });
        await page.waitForTimeout(300); // Brief pause after dismiss
        break; // Only dismiss one dialog per page load
      }
    } catch (e) {
      // Selector not found or not clickable, continue
    }
  }
}

mountSystemRoutes(app, {
  flyMachineId: FLY_MACHINE_ID,
  getBrowserRunning: () => browser !== null && (browser.isConnected?.() ?? false),
  getRegister,
  getTotalTabCount,
  healthState,
  proxyPool,
  scheduleBrowserWarmRetry,
  sessions,
});

mountTabLifecycleRoutes(app, {
  attachDownloadListener,
  clearTabDownloads,
  createTabState,
  findTab,
  fly,
  getSession,
  getTabGroup,
  getTotalTabCount,
  handleRouteError,
  log,
  maxTabsGlobal: MAX_TABS_GLOBAL,
  maxTabsPerSession: MAX_TABS_PER_SESSION,
  normalizeUserId,
  pluginEvents,
  recycleOldestTab,
  refreshActiveTabsGauge,
  refreshTabLockQueueDepth,
  requestTimeoutMs,
  safePageClose,
  sessions,
  tabLocks,
  validateUrl,
  withPageLoadDuration,
  withTimeout,
});

mountTabNavigationRoutes(app, {
  attachDownloadListener,
  browserRestartsTotal,
  buildRefs,
  closeSession,
  createTabState,
  ensureBrowser,
  expandMacro,
  findTab,
  getBrowserLaunchProxy: () => browserLaunchProxy,
  getSession,
  getTabGroup,
  getTotalTabCount,
  handleRouteError,
  isGoogleSearchBlocked,
  isGoogleSearchUrl,
  isGoogleSerp,
  log,
  maxTabsGlobal: MAX_TABS_GLOBAL,
  maxTabsPerSession: MAX_TABS_PER_SESSION,
  normalizeUserId,
  pluginEvents,
  proxyPool,
  recycleOldestTab,
  refreshActiveTabsGauge,
  requestTimeoutMs,
  safeError,
  sessions,
  validateUrl,
  withPageLoadDuration,
  withTabLock,
  withTimeout,
  withUserLimit,
});

mountTabSnapshotRoutes(app, {
  extractGoogleSerp,
  findTab,
  getAriaSnapshot,
  handleRouteError,
  interactiveRoles: INTERACTIVE_ROLES,
  isGoogleSearchBlocked,
  isGoogleSearchUrl,
  isGoogleSerp,
  isGoogleUnavailable,
  log,
  normalizeUserId,
  pluginEvents,
  proxyPool,
  refreshTabRefs,
  requestTimeoutMs,
  rotateGoogleTab,
  sessions,
  skipPatterns: SKIP_PATTERNS,
  snapshotBytes,
  windowSnapshot,
  withTimeout,
  withUserLimit,
});

mountTabInteractionRoutes(app, {
  findTab,
  handleRouteError,
  log,
  normalizeUserId,
  pluginEvents,
  sessions,
  waitForPageReady,
  withTabLock,
});

mountTabClickRoutes(app, {
  StaleRefsError,
  findTab,
  handleRouteError,
  handlerTimeoutMs: HANDLER_TIMEOUT_MS,
  isGoogleSerp,
  log,
  normalizeUserId,
  pluginEvents,
  refToLocator,
  refreshTabRefs,
  safeError,
  sessions,
  withTabLock,
  withUserLimit,
});

mountTabTypingRoutes(app, {
  StaleRefsError,
  findTab,
  handleRouteError,
  log,
  normalizeUserId,
  pluginEvents,
  refToLocator,
  refreshTabRefs,
  safeError,
  sessions,
  withTabLock,
});

mountTabHistoryRoutes(app, {
  buildRefs,
  findTab,
  handleRouteError,
  log,
  normalizeUserId,
  sessions,
  withTabLock,
});

mountTabContentRoutes(app, {
  classifyError,
  failuresTotal,
  findTab,
  handleRouteError,
  log,
  normalizeUserId,
  pluginEvents,
  safeError,
  sessions,
});

mountTabEvaluationRoutes(app, {
  classifyError,
  failuresTotal,
  findTab,
  log,
  normalizeUserId,
  pluginEvents,
  safeError,
  sessions,
});

mountTraceRoutes(app, {
  authMiddleware,
  log,
  normalizeUserId,
  tracesDir: CONFIG.tracesDir,
});
mountSessionRoutes(app, {
  closeSession,
  config: CONFIG,
  failuresTotal,
  getSession,
  handleRouteError,
  log,
  normalizeUserId,
  pluginEvents,
  safeError,
  scheduleBrowserIdleShutdown,
  sessions,
});

// Cleanup stale sessions
setInterval(() => {
  const now = Date.now();
  for (const [userId, session] of Array.from(sessions.entries())) {
    if (now - session.lastAccess > SESSION_TIMEOUT_MS) {
      session._closing = true;
      const idleMs = now - session.lastAccess;
      sessionsExpiredTotal.inc();
      pluginEvents.emit('session:expired', { userId, idleMs });
      closeSession(userId, session, {
        reason: 'session_timeout',
        clearDownloads: true,
        clearLocks: true,
      }).catch(() => {});
      log('info', 'session expired', { userId });
    }
  }
  // When all sessions gone, start idle timer to kill browser
  if (sessions.size === 0) {
    scheduleBrowserIdleShutdown();
  }
  refreshTabLockQueueDepth();
}, 60_000);

// Per-tab inactivity reaper -- close tabs idle for TAB_INACTIVITY_MS
setInterval(() => {
  const now = Date.now();
  for (const [userId, session] of sessions) {
    for (const [listItemId, group] of session.tabGroups) {
      for (const [tabId, tabState] of group) {
        if (!tabState._lastReaperCheck) {
          tabState._lastReaperCheck = now;
          tabState._lastReaperToolCalls = tabState.toolCalls;
          continue;
        }
        if (tabState.toolCalls === tabState._lastReaperToolCalls) {
          const idleMs = now - tabState._lastReaperCheck;
          if (idleMs >= TAB_INACTIVITY_MS) {
            tabsReapedTotal.inc();
            log('info', 'tab reaped (inactive)', {
              userId,
              tabId,
              listItemId,
              idleMs,
              toolCalls: tabState.toolCalls,
            });
            safePageClose(tabState.page);
            group.delete(tabId);
            {
              const _l = tabLocks.get(tabId);
              if (_l) _l.drain();
              tabLocks.delete(tabId);
            }
            refreshTabLockQueueDepth();
            refreshActiveTabsGauge();
          }
        } else {
          tabState._lastReaperCheck = now;
          tabState._lastReaperToolCalls = tabState.toolCalls;
        }
      }
      if (group.size === 0) {
        session.tabGroups.delete(listItemId);
      }
    }
    // Clean up sessions with zero tabs remaining -- free browser context memory
    if (session.tabGroups.size === 0) {
      session._closing = true;
      log('info', 'session empty after tab reaper, closing', { userId });
      closeSession(userId, session, {
        reason: 'tab_reaper_empty_session',
        clearDownloads: true,
        clearLocks: true,
      }).catch(() => {});
      sessionsExpiredTotal.inc();
    }
  }
  if (sessions.size === 0) scheduleBrowserIdleShutdown();
}, 60_000);

// Native memory pressure restart -- when all sessions are gone and Firefox's
// native memory has grown beyond threshold, kill the browser immediately instead
// of waiting for the idle timer. Firefox/Camoufox doesn't fully reclaim native
// memory after context.close() due to jemalloc fragmentation, JIT caches, and
// NSS/TLS session caches. See #1032.
setInterval(() => {
  if (sessions.size > 0 || !browser) return;
  const mem = process.memoryUsage();
  const nativeMemMb = Math.round((mem.rss - mem.heapUsed) / 1048576);
  if (_nativeMemBaseline === null) {
    _nativeMemBaseline = nativeMemMb;
    return;
  }
  const growth = nativeMemMb - _nativeMemBaseline;
  if (growth >= NATIVE_MEM_RESTART_THRESHOLD_MB) {
    log('warn', 'native memory pressure, restarting browser', {
      baselineMb: _nativeMemBaseline,
      currentMb: nativeMemMb,
      growthMb: growth,
      thresholdMb: NATIVE_MEM_RESTART_THRESHOLD_MB,
    });
    browserRestartsTotal.labels('memory_pressure').inc();
    closeBrowserFully('memory_pressure').catch((err) => {
      log('error', 'memory pressure browser close failed', {
        error: err.message,
      });
    });
  }
}, 30_000);

mountLegacyCoreRoutes(app, {
  attachDownloadListener,
  buildRefs,
  closeAllSessions,
  closeBrowserFully,
  config: CONFIG,
  createTabState,
  ensureBrowser,
  failuresTotal,
  findTab,
  fly,
  getBrowser: () => browser,
  getSession,
  getTabGroup,
  getTotalTabCount,
  handleRouteError,
  isGoogleSerp,
  log,
  maxTabsGlobal: MAX_TABS_GLOBAL,
  maxTabsPerSession: MAX_TABS_PER_SESSION,
  normalizeUserId,
  pluginEvents,
  recycleOldestTab,
  refreshActiveTabsGauge,
  safeError,
  sessions,
  timingSafeCompare,
  validateUrl,
  withPageLoadDuration,
  withTabLock,
});

mountLegacySnapshotRoutes(app, {
  buildRefs,
  extractGoogleSerp,
  findTab,
  getAriaSnapshot,
  handleRouteError,
  isGoogleSerp,
  log,
  normalizeUserId,
  sessions,
  snapshotBytes,
  windowSnapshot,
});

mountLegacyActionRoutes(app, {
  StaleRefsError,
  buildRefs,
  findTab,
  handleRouteError,
  log,
  normalizeUserId,
  refToLocator,
  safePageClose,
  sessions,
  tabLocks,
  withTabLock,
});

// Periodic stats beacon (every 5 min)
setInterval(() => {
  const mem = process.memoryUsage();
  let totalTabs = 0;
  for (const [, session] of sessions) {
    for (const [, group] of session.tabGroups) {
      totalTabs += group.size;
    }
  }
  log('info', 'stats', {
    sessions: sessions.size,
    tabs: totalTabs,
    rssBytes: mem.rss,
    heapUsedBytes: mem.heapUsed,
    uptimeSeconds: Math.floor(process.uptime()),
    browserConnected: browser?.isConnected() ?? false,
  });
}, 5 * 60_000);

// Active health probe -- detect hung browser even when isConnected() lies
setInterval(async () => {
  if (!browser || healthState.isRecovering) return;
  const timeSinceSuccess = Date.now() - healthState.lastSuccessfulNav;
  // Skip probe if operations are in flight AND last success was recent.
  // If it's been >120s since any successful operation, probe anyway --
  // active ops are likely stuck on a frozen browser and will time out eventually.
  if (healthState.activeOps > 0 && timeSinceSuccess < 120000) {
    log('info', 'health probe skipped, operations active', {
      activeOps: healthState.activeOps,
    });
    return;
  }
  if (timeSinceSuccess < 120000) return;

  if (healthState.activeOps > 0) {
    log('warn', 'health probe forced despite active ops', {
      activeOps: healthState.activeOps,
      timeSinceSuccessMs: timeSinceSuccess,
    });
  }

  let testContext;
  try {
    testContext = await browser.newContext();
    const page = await testContext.newPage();
    await page.goto('about:blank', { timeout: 5000 });
    await page.close();
    await testContext.close();
    healthState.lastSuccessfulNav = Date.now();
  } catch (err) {
    failuresTotal.labels('health_probe', 'internal').inc();
    log('warn', 'health probe failed', {
      error: err.message,
      timeSinceSuccessMs: timeSinceSuccess,
    });
    if (testContext) await testContext.close().catch(() => {});
    restartBrowser('health probe failed').catch(() => {});
  }
}, 60_000);

// Crash logging
process.on('uncaughtException', (err) => {
  pluginEvents.emit('browser:error', { error: err });
  log('error', 'uncaughtException', { error: err.message, stack: err.stack });
  reporter.reportCrash(err, { resourceOpts: _resourceOpts() });
  process.exit(1);
});
process.on('unhandledRejection', (reason) => {
  log('error', 'unhandledRejection', { reason: String(reason) });
});

// Graceful shutdown
let shuttingDown = false;

async function gracefulShutdown(signal) {
  if (shuttingDown) return;
  shuttingDown = true;
  log('info', 'shutting down', { signal });
  pluginEvents.emit('server:shutdown', { signal });

  const forceTimeout = setTimeout(() => {
    log('error', 'shutdown timed out, forcing exit');
    process.exit(1);
  }, 10000);
  forceTimeout.unref();

  server.close();
  stopMemoryReporter();

  await closeAllSessions(`shutdown:${signal}`, {
    clearDownloads: false,
    clearLocks: false,
  });

  await closeBrowserFully(`shutdown:${signal}`);
  process.exit(0);
}

process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
process.on('SIGINT', () => gracefulShutdown('SIGINT'));

// Idle self-shutdown REMOVED -- it was racing with min_machines_running=2
// and stopping machines that Fly couldn't auto-restart fast enough, leaving
// only 1 machine to handle all browser traffic (causing timeouts for users).
// Fly's auto_stop_machines=false + min_machines_running=2 handles scaling.

const PORT = CONFIG.port;
const HOST = CONFIG.host || '127.0.0.1';
if (CONFIG.nodeEnv === 'production' && !CONFIG.accessKey) {
  throw new Error('CAMOFOX_ACCESS_KEY is required when NODE_ENV=production');
}
if (!_isLoopbackAddress(HOST) && !CONFIG.accessKey) {
  throw new Error(
    'CAMOFOX_ACCESS_KEY is required when CAMOFOX_HOST is not loopback',
  );
}
pluginEvents.emit('server:starting', { host: HOST, port: PORT });

// Load plugins before starting the server
const pluginCtx = {
  sessions,
  config: CONFIG,
  log,
  events: pluginEvents,
  auth: authMiddleware,
  ensureBrowser,
  getSession,
  destroySession,
  closeSession,
  withUserLimit,
  safePageClose,
  normalizeUserId,
  validateUrl,
  safeError,
  buildProxyUrl,
  proxyPool,
  failuresTotal,
  metricsRegistry: getRegister,
  createMetric,
  /** Factory for Xvfb virtual display. Plugins can replace this to customise resolution/args. */
  createVirtualDisplay: () => new VirtualDisplay(),
  /** The upstream VirtualDisplay class -- plugins can subclass it. */
  VirtualDisplay,
};
const loadedPlugins = await loadPlugins(app, pluginCtx);

// --- OpenAPI docs (after all routes are registered) ---
mountDocs(app);

const server = app.listen(PORT, HOST, async () => {
  startMemoryReporter();
  refreshActiveTabsGauge();
  refreshTabLockQueueDepth();
  pluginEvents.emit('server:started', {
    host: HOST,
    port: PORT,
    pid: process.pid,
    plugins: loadedPlugins,
  });
  if (FLY_MACHINE_ID) {
    log('info', 'server started (fly)', {
      host: HOST,
      port: PORT,
      pid: process.pid,
      machineId: FLY_MACHINE_ID,
      nodeVersion: process.version,
    });
  } else {
    log('info', 'server started', {
      host: HOST,
      port: PORT,
      pid: process.pid,
      nodeVersion: process.version,
    });
  }
  const tmpCleanup = cleanupOrphanedTempFiles({ tmpDir: os.tmpdir() });
  if (tmpCleanup.removed > 0) {
    log('info', 'cleaned up orphaned camoufox temp files', tmpCleanup);
  }
  const profileCleanup = cleanupStaleFirefoxProfiles();
  if (profileCleanup.removed > 0) {
    log('info', 'cleaned up stale firefox profiles on startup', profileCleanup);
  }

  // Periodic temp profile cleanup every 10 minutes
  setInterval(
    () => {
      try {
        const cleaned = cleanupStaleFirefoxProfiles();
        if (cleaned.removed > 0) {
          log('info', 'periodic firefox profile cleanup', cleaned);
        }
      } catch {
        /* best effort */
      }
    },
    10 * 60 * 1000,
  ).unref();
  const traceSweep = sweepOldTraces({
    baseDir: CONFIG.tracesDir,
    ttlMs: CONFIG.tracesTtlHours * 3600 * 1000,
    maxBytesPerFile: CONFIG.tracesMaxBytes,
  });
  if (traceSweep.removedTtl > 0 || traceSweep.removedOversized > 0) {
    log('info', 'swept old traces', traceSweep);
  }
  if (CONFIG.browserPrewarmEnabled) {
    // Pre-warm only when explicitly requested. On some macOS hosts Camoufox can
    // SIGABRT during headless startup; Agentic Trader keeps launch on-demand to
    // avoid browser crash loops while still exposing helper readiness.
    try {
      const start = Date.now();
      await ensureBrowser();
      log('info', 'browser pre-warmed', { ms: Date.now() - start });
      scheduleBrowserIdleShutdown();
    } catch (err) {
      log('error', 'browser pre-warm failed (will retry in background)', {
        error: err.message,
      });
      scheduleBrowserWarmRetry();
    }
  } else {
    log('info', 'browser pre-warm disabled; browser launches on demand');
  }
  // Idle self-shutdown removed -- Fly manages machine lifecycle via fly.toml.
});

server.on('error', (err) => {
  if (err.code === 'EADDRINUSE') {
    log('error', 'port in use', { port: PORT });
    process.exit(1);
  }
  log('error', 'server error', { error: err.message });
  process.exit(1);
});
