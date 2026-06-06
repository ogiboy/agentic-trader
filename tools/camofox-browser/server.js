import { VirtualDisplay } from 'camoufox-js/dist/virtdisplay.js';
import { createBrowserLifecycle } from './lib/browser-lifecycle.js';
import { createBrowserProcess } from './lib/browser-process.js';
import { loadConfig } from './lib/config.js';
import {
  attachDownloadListener,
  clearSessionDownloads,
  clearTabDownloads,
} from './lib/downloads.js';
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
import { createRouteErrorHandler } from './lib/route-error-handler.js';
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
import { createJsonLogger } from './lib/logging.js';
import { createServerApp } from './lib/server/app.js';
import { createRouteContext } from './lib/server/route-context.js';
import {
  createHealthState,
  createRequestTimeoutMs,
  createRuntimeSettings,
  logProxyPool,
} from './lib/server/runtime-settings.js';
import {
  mountRuntimeMonitors,
  startServerBootstrap,
} from './lib/server/startup.js';
import { createTabMetrics } from './lib/server/tab-metrics.js';
import { cleanupStaleFirefoxProfiles } from './lib/tmp-cleanup.js';

const CONFIG = loadConfig();

// --- Plugin event bus ---
const pluginEvents = createPluginEvents();
let pluginCtx = null;

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
const log = createJsonLogger();

const {
  extractGoogleSerp,
  isGoogleSearchBlocked,
  isGoogleSearchUrl,
  isGoogleSerp,
} = createGoogleSerpHelpers({ log });
const { waitForPageReady } = createPageReadiness({ log });

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
const { getTotalTabCount, refreshActiveTabsGauge, withPageLoadDuration } =
  createTabMetrics({
    activeTabsGauge,
    pageLoadDuration,
    sessions,
  });
const { getResourceOpts: _resourceOpts, reporter } = createServerReporting({
  config: CONFIG,
  getBrowser: () => browser,
  sessions,
});
const { app, authMiddleware, fly, flyMachineId, timingSafeCompare } =
  createServerApp({
    config: CONFIG,
    log,
    reporter,
    requestDuration,
    requestsTotal,
  });
const runtimeSettings = createRuntimeSettings(CONFIG);
let _nativeMemBaseline = null; // RSS - heapUsed at first idle measurement
const healthState = createHealthState();

const { closeBrowserFully, getHostOS, safePageClose } = createBrowserProcess({
  cleanupStaleFirefoxProfiles,
  getBrowser: () => browser,
  getLastBrowserPid: () => _lastBrowserPid,
  log,
  pageCloseTimeoutMs: runtimeSettings.pageCloseTimeoutMs,
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
    buildrefsTimeoutMs: runtimeSettings.buildrefsTimeoutMs,
    extractGoogleSerp,
    isGoogleSerp,
    log,
    maxSnapshotNodes: runtimeSettings.maxSnapshotNodes,
    waitForPageReady,
  });

// Proxy strategy for outbound browsing.
const proxyPool = createProxyPool(CONFIG.proxy);
logProxyPool({ config: CONFIG, log, proxyPool });
const requestTimeoutMs = createRequestTimeoutMs({
  handlerTimeoutMs: runtimeSettings.handlerTimeoutMs,
  proxyPool,
});

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
  handlerTimeoutMs: runtimeSettings.handlerTimeoutMs,
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
  maxConsecutiveTimeouts: runtimeSettings.maxConsecutiveTimeouts,
  normalizeUserId,
  pluginEvents,
  proxyPool,
  reporter,
  sendError,
  sessions,
});

const routeContext = createRouteContext({
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
  flyMachineId,
  getAriaSnapshot,
  getBrowser: () => browser,
  getBrowserLaunchProxy,
  getRegister,
  getSession,
  getTabGroup,
  getTotalTabCount,
  handleRouteError,
  handlerTimeoutMs: runtimeSettings.handlerTimeoutMs,
  healthState,
  interactiveRoles: INTERACTIVE_ROLES,
  isGoogleSearchBlocked,
  isGoogleSearchUrl,
  isGoogleSerp,
  isGoogleUnavailable,
  log,
  maxTabsGlobal: runtimeSettings.maxTabsGlobal,
  maxTabsPerSession: runtimeSettings.maxTabsPerSession,
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
  validateUrl,
  waitForPageReady,
  windowSnapshot,
  withPageLoadDuration,
  withTabLock,
  withTimeout,
  withUserLimit,
});

mountCamofoxRoutes(app, routeContext);

mountRuntimeMonitors({
  browserRestartsTotal,
  closeBrowserFully,
  closeSession,
  failuresTotal,
  getBrowser: () => browser,
  getNativeMemBaseline: () => _nativeMemBaseline,
  healthState,
  log,
  nativeMemRestartThresholdMb: runtimeSettings.nativeMemRestartThresholdMb,
  refreshActiveTabsGauge,
  refreshTabLockQueueDepth,
  restartBrowser,
  safePageClose,
  scheduleBrowserIdleShutdown,
  sessionTimeoutMs: runtimeSettings.sessionTimeoutMs,
  sessions,
  setNativeMemBaseline: (value) => {
    _nativeMemBaseline = value;
  },
  tabInactivityMs: runtimeSettings.tabInactivityMs,
  tabLocks,
  tabsReapedTotal,
  sessionsExpiredTotal,
});

await startServerBootstrap({
  app,
  authMiddleware,
  closeAllSessions,
  closeBrowserFully,
  closeSession,
  config: CONFIG,
  destroySession,
  ensureBrowser,
  failuresTotal,
  flyMachineId,
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
