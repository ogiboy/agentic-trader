import { VirtualDisplay } from 'camoufox-js/dist/virtdisplay.js';
import express from 'express';
import {
  timingSafeCompare as _timingSafeCompare,
  accessKeyMiddleware,
  requireAuth,
} from './lib/auth.js';
import { createBrowserLifecycle } from './lib/browser-lifecycle.js';
import { createBrowserProcess } from './lib/browser-process.js';
import { loadConfig } from './lib/config.js';
import {
  attachDownloadListener,
  clearSessionDownloads,
  clearTabDownloads,
} from './lib/downloads.js';
import { createFlyHelpers } from './lib/fly.js';
import { expandMacro } from './lib/macros.js';
import { createPageReadiness } from './lib/page-readiness.js';
import { createPluginEvents } from './lib/plugins.js';
import { createProxyPool, normalizePlaywrightProxy } from './lib/proxy.js';
import {
  INTERACTIVE_ROLES,
  SKIP_PATTERNS,
  StaleRefsError,
  createRefHelpers,
} from './lib/refs.js';
import { createRouteSafety } from './lib/route-safety.js';
import { createGoogleSerpHelpers } from './lib/google-serp.js';
import {
  createRuntimeConcurrency,
  normalizeUserId,
} from './lib/runtime-concurrency.js';
import { createRequestLoggingMiddleware } from './lib/request-logging.js';
import { createRouteErrorHandler } from './lib/route-error-handler.js';
import { startRuntimeMonitors } from './lib/runtime-monitors.js';
import { startCamofoxServer } from './lib/server-bootstrap.js';
import { createSessionManager } from './lib/session-manager.js';
import { createServerReporting } from './lib/server-reporting.js';
import { windowSnapshot } from './lib/snapshot.js';
import { createTabStateManager } from './lib/tab-state.js';
import {
  ensureTracesDir,
  makeTraceFilename,
  tracePathFor,
} from './lib/tracing.js';

import { coalesceInflight } from './lib/inflight.js';
import { getRegister, initMetrics } from './lib/metrics.js';
import { mountCamofoxRoutes } from './lib/routes/index.js';
import {
  classifyProxyError,
  createTabHealthTracker,
} from './lib/reporter.js';
import { actionFromReq, classifyError } from './lib/request-utils.js';
import { cleanupStaleFirefoxProfiles } from './lib/tmp-cleanup.js';

const CONFIG = loadConfig();

// --- Plugin event bus ---
const pluginEvents = createPluginEvents();
let pluginCtx = null;

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
const { waitForPageReady } = createPageReadiness({ log });

const app = express();
app.use(express.json({ limit: '100kb' }));

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

// timingSafeCompare imported from lib/auth.js
const timingSafeCompare = _timingSafeCompare;

const { safeError, sendError, validateUrl } = createRouteSafety({
  config: CONFIG,
  log,
  StaleRefsError,
});

let browser = null;
let _lastBrowserPid = null; // Track PID independently for force-kill after close
// userId -> { context, tabGroups: Map<sessionKey, Map<tabId, TabState>>, lastAccess }
// TabState = { page, refs: Map<refId, {role, name, nth}>, visitedUrls: Set, downloads: Array, toolCalls: number }
// Note: sessionKey was previously called listItemId - both are accepted for backward compatibility
const sessions = new Map();
const { getResourceOpts: _resourceOpts, reporter } = createServerReporting({
  config: CONFIG,
  getBrowser: () => browser,
  sessions,
});
app.use(
  createRequestLoggingMiddleware({
    log,
    reporter,
    requestDuration,
    requestsTotal,
  }),
);


const SESSION_TIMEOUT_MS = CONFIG.sessionTimeoutMs;
const MAX_SNAPSHOT_NODES = 500;
const TAB_INACTIVITY_MS = CONFIG.tabInactivityMs;
const MAX_TABS_PER_SESSION = CONFIG.maxTabsPerSession;
const MAX_TABS_GLOBAL = CONFIG.maxTabsGlobal;
const HANDLER_TIMEOUT_MS = CONFIG.handlerTimeoutMs;
const PAGE_CLOSE_TIMEOUT_MS = 5000;
const BUILDREFS_TIMEOUT_MS = CONFIG.buildrefsTimeoutMs;
const NATIVE_MEM_RESTART_THRESHOLD_MB = CONFIG.nativeMemRestartThresholdMb;
let _nativeMemBaseline = null; // RSS - heapUsed at first idle measurement
const FAILURE_THRESHOLD = 3;
const MAX_CONSECUTIVE_TIMEOUTS = 3;

const { closeBrowserFully, getHostOS, safePageClose } = createBrowserProcess({
  cleanupStaleFirefoxProfiles,
  getBrowser: () => browser,
  getLastBrowserPid: () => _lastBrowserPid,
  log,
  pageCloseTimeoutMs: PAGE_CLOSE_TIMEOUT_MS,
  reporter,
  resetNativeMemBaseline: () => {
    _nativeMemBaseline = null;
  },
  setBrowser: (value) => {
    browser = value;
  },
  setLastBrowserPid: (value) => {
    _lastBrowserPid = value;
  },
});

const { buildRefs, getAriaSnapshot, refToLocator, refreshTabRefs } =
  createRefHelpers({
    buildrefsTimeoutMs: BUILDREFS_TIMEOUT_MS,
    extractGoogleSerp,
    isGoogleSerp,
    log,
    maxSnapshotNodes: MAX_SNAPSHOT_NODES,
    waitForPageReady,
  });

function requestTimeoutMs(baseMs = HANDLER_TIMEOUT_MS) {
  return proxyPool?.canRotateSessions ? Math.max(baseMs, 180000) : baseMs;
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

// --- Browser health tracking ---
const healthState = {
  consecutiveNavFailures: 0,
  lastSuccessfulNav: Date.now(),
  isRecovering: false,
  activeOps: 0,
};

const {
  ensureBrowser,
  getBrowserLaunchProxy,
  restartBrowser,
  scheduleBrowserIdleShutdown,
  scheduleBrowserWarmRetry,
} = createBrowserLifecycle({
  browserRestartsTotal,
  closeAllSessions: (...args) => closeAllSessions(...args),
  closeBrowserFully,
  config: CONFIG,
  createVirtualDisplay: () =>
    pluginCtx?.createVirtualDisplay?.() ?? new VirtualDisplay(),
  failuresTotal,
  getBrowser: () => browser,
  getHostOS,
  isGoogleSearchBlocked,
  isGoogleSerp,
  log,
  normalizePlaywrightProxy,
  pluginEvents,
  proxyPool,
  sessions,
  setBrowser: (value) => {
    browser = value;
  },
  setLastBrowserPid: (value) => {
    _lastBrowserPid = value;
  },
});

const {
  clearSessionLocks,
  refreshTabLockQueueDepth,
  tabLocks,
  withTabLock,
  withTimeout,
  withUserLimit,
} = createRuntimeConcurrency({
  handlerTimeoutMs: HANDLER_TIMEOUT_MS,
  healthState,
  maxConcurrentPerUser: CONFIG.maxConcurrentPerUser,
  tabLockQueueDepth,
  tabLockTimeoutsTotal,
});

const { closeAllSessions, closeSession, destroySession, getSession } =
  createSessionManager({
    clearSessionDownloads,
    clearSessionLocks,
    coalesceInflight,
    config: CONFIG,
    ensureBrowser,
    ensureTracesDir,
    getBrowserLaunchProxy,
    log,
    makeTraceFilename,
    normalizePlaywrightProxy,
    normalizeUserId,
    pluginEvents,
    proxyPool,
    refreshActiveTabsGauge,
    sessions,
    tracePathFor,
  });

const {
  createTabState,
  destroyTab,
  findTab,
  getTabGroup,
  isGoogleUnavailable,
  recycleOldestTab,
  rotateGoogleTab,
} = createTabStateManager({
  attachDownloadListener,
  browserRestartsTotal,
  closeSession,
  createTabHealthTracker,
  getSession,
  isGoogleSearchUrl,
  log,
  normalizeUserId,
  pluginEvents,
  refreshActiveTabsGauge,
  refreshTabLockQueueDepth,
  safePageClose,
  sessions,
  tabLocks,
  tabsDestroyedTotal,
  tabsRecycledTotal,
  withPageLoadDuration,
});

const { handleRouteError } = createRouteErrorHandler({
  actionFromReq,
  browserRestartsTotal,
  classifyError,
  classifyProxyError,
  config: CONFIG,
  destroySession,
  destroyTab,
  failuresTotal,
  findTab,
  getResourceOpts: _resourceOpts,
  log,
  maxConsecutiveTimeouts: MAX_CONSECUTIVE_TIMEOUTS,
  normalizeUserId,
  pluginEvents,
  proxyPool,
  reporter,
  sendError,
  sessions,
});

function getTotalTabCount() {
  let total = 0;
  for (const session of sessions.values()) {
    for (const group of session.tabGroups.values()) {
      total += group.size;
    }
  }
  return total;
}

function refreshActiveTabsGauge() {
  activeTabsGauge.set(getTotalTabCount());
}

async function withPageLoadDuration(action, fn) {
  const end = pageLoadDuration.startTimer();
  try {
    return await fn();
  } finally {
    end();
  }
}

mountCamofoxRoutes(app, {
  StaleRefsError,
  attachDownloadListener,
  authMiddleware,
  browserRestartsTotal,
  buildRefs,
  classifyError,
  clearTabDownloads,
  closeAllSessions,
  closeBrowserFully,
  closeSession,
  config: CONFIG,
  createTabState,
  ensureBrowser,
  expandMacro,
  extractGoogleSerp,
  failuresTotal,
  findTab,
  fly,
  flyMachineId: FLY_MACHINE_ID,
  getAriaSnapshot,
  getBrowser: () => browser,
  getBrowserLaunchProxy,
  getBrowserRunning: () => browser !== null && (browser.isConnected?.() ?? false),
  getRegister,
  getSession,
  getTabGroup,
  getTotalTabCount,
  handleRouteError,
  handlerTimeoutMs: HANDLER_TIMEOUT_MS,
  healthState,
  interactiveRoles: INTERACTIVE_ROLES,
  isGoogleSearchBlocked,
  isGoogleSearchUrl,
  isGoogleSerp,
  isGoogleUnavailable,
  log,
  maxTabsGlobal: MAX_TABS_GLOBAL,
  maxTabsPerSession: MAX_TABS_PER_SESSION,
  normalizeUserId,
  pluginEvents,
  proxyPool,
  recycleOldestTab,
  refToLocator,
  refreshActiveTabsGauge,
  refreshTabLockQueueDepth,
  refreshTabRefs,
  requestTimeoutMs,
  rotateGoogleTab,
  safeError,
  safePageClose,
  scheduleBrowserIdleShutdown,
  scheduleBrowserWarmRetry,
  sessions,
  skipPatterns: SKIP_PATTERNS,
  snapshotBytes,
  tabLocks,
  timingSafeCompare,
  tracesDir: CONFIG.tracesDir,
  validateUrl,
  waitForPageReady,
  windowSnapshot,
  withPageLoadDuration,
  withTabLock,
  withTimeout,
  withUserLimit,
});

startRuntimeMonitors({
  browserRestartsTotal,
  closeBrowserFully,
  closeSession,
  failuresTotal,
  getBrowser: () => browser,
  getNativeMemBaseline: () => _nativeMemBaseline,
  healthState,
  log,
  nativeMemRestartThresholdMb: NATIVE_MEM_RESTART_THRESHOLD_MB,
  refreshActiveTabsGauge,
  refreshTabLockQueueDepth,
  restartBrowser,
  safePageClose,
  scheduleBrowserIdleShutdown,
  sessionTimeoutMs: SESSION_TIMEOUT_MS,
  sessions,
  setNativeMemBaseline: (value) => {
    _nativeMemBaseline = value;
  },
  tabInactivityMs: TAB_INACTIVITY_MS,
  tabLocks,
  tabsReapedTotal,
  sessionsExpiredTotal,
});

await startCamofoxServer({
  app,
  authMiddleware,
  closeAllSessions,
  closeBrowserFully,
  closeSession,
  config: CONFIG,
  destroySession,
  ensureBrowser,
  failuresTotal,
  flyMachineId: FLY_MACHINE_ID,
  getRegister,
  getResourceOpts: _resourceOpts,
  getSession,
  log,
  normalizeUserId,
  pluginEvents,
  proxyPool,
  refreshActiveTabsGauge,
  refreshTabLockQueueDepth,
  reporter,
  safeError,
  safePageClose,
  scheduleBrowserIdleShutdown,
  scheduleBrowserWarmRetry,
  sessions,
  setPluginContext: (value) => {
    pluginCtx = value;
  },
  validateUrl,
  withUserLimit,
});
