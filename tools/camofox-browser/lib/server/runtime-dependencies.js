import { VirtualDisplay } from 'camoufox-js/dist/virtdisplay.js';
import { createBrowserLifecycle } from '../browser-lifecycle.js';
import { createBrowserProcess } from '../browser-process.js';
import {
  attachDownloadListener,
  clearSessionDownloads,
  clearTabDownloads,
} from '../downloads.js';
import { expandMacro } from '../macros.js';
import { createPageReadiness } from '../page-readiness.js';
import { createPluginEvents } from '../plugins.js';
import { createProxyPool, normalizePlaywrightProxy } from '../proxy.js';
import {
  INTERACTIVE_ROLES,
  SKIP_PATTERNS,
  StaleRefsError,
  createRefHelpers,
} from '../refs.js';
import { createRouteSafety } from '../route-safety.js';
import { createGoogleSerpHelpers } from '../google-serp.js';
import {
  createRuntimeConcurrency,
  normalizeUserId,
} from '../runtime-concurrency.js';
import { createRouteErrorHandler } from '../route-error-handler.js';
import { createSessionManager } from '../session-manager.js';
import { createServerReporting } from '../server-reporting.js';
import { windowSnapshot } from '../snapshot.js';
import { createTabStateManager } from '../tab-state.js';
import {
  ensureTracesDir,
  makeTraceFilename,
  tracePathFor,
} from '../tracing.js';

import { coalesceInflight } from '../inflight.js';
import { getRegister, initMetrics } from '../metrics.js';
import {
  classifyProxyError,
  createTabHealthTracker,
} from '../reporter.js';
import { actionFromReq, classifyError } from '../request-utils.js';
import { createServerApp } from './app.js';
import { createRouteContext } from './route-context.js';
import {
  createHealthState,
  createRequestTimeoutMs,
  createRuntimeSettings,
  logProxyPool,
} from './runtime-settings.js';
import { createTabMetrics } from './tab-metrics.js';
import { cleanupStaleFirefoxProfiles } from '../tmp-cleanup.js';
import { createMutableRuntimeState } from './runtime-state.js';

/**
 * Build and initialize the full Camofox server runtime, wiring together metrics, plugin events, browser lifecycle, session/tab management, routing, error handling, concurrency controls, and proxying.
 * @param {Object} config - Server configuration object.
 * @param {Object} log - Logger used by the runtime.
 * @returns {Object} An API object exposing the initialized server app and middleware, lifecycle and session/tab management functions, metrics and counters, proxy pool and request timeout settings, route context and error/safety helpers, health state, and concurrency utilities.
 */
export async function createCamofoxServerRuntime({ config, log }) {
  const CONFIG = config;

  // --- Plugin event bus ---
  const pluginEvents = createPluginEvents();
  const state = createMutableRuntimeState();
  const { sessions } = state;

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

  const { getTotalTabCount, refreshActiveTabsGauge, withPageLoadDuration } =
    createTabMetrics({
      activeTabsGauge,
      pageLoadDuration,
      sessions,
    });
  const { getResourceOpts: _resourceOpts, reporter } = createServerReporting({
    config: CONFIG,
    getBrowser: state.getBrowser,
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
  const healthState = createHealthState();

  const { closeBrowserFully, getHostOS, safePageClose } = createBrowserProcess({
    cleanupStaleFirefoxProfiles,
    getBrowser: state.getBrowser,
    getLastBrowserPid: state.getLastBrowserPid,
    log,
    pageCloseTimeoutMs: runtimeSettings.pageCloseTimeoutMs,
    reporter,
    resetNativeMemBaseline: state.resetNativeMemBaseline,
    setBrowser: state.setBrowser,
    setLastBrowserPid: state.setLastBrowserPid,
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
      state.getPluginContext()?.createVirtualDisplay?.() ?? new VirtualDisplay(),
    failuresTotal,
    getBrowser: state.getBrowser,
    getHostOS,
    isGoogleSearchBlocked,
    isGoogleSerp,
    log,
    normalizePlaywrightProxy,
    pluginEvents,
    proxyPool,
    sessions,
    setBrowser: state.setBrowser,
    setLastBrowserPid: state.setLastBrowserPid,
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
    getBrowser: state.getBrowser,
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

  return {
    app,
    authMiddleware,
    browserRestartsTotal,
    closeAllSessions,
    closeBrowserFully,
    closeSession,
    config: CONFIG,
    destroySession,
    ensureBrowser,
    failuresTotal,
    flyMachineId,
    getBrowser: state.getBrowser,
    getNativeMemBaseline: state.getNativeMemBaseline,
    getRegister,
    getResourceOpts: _resourceOpts,
    getSession,
    healthState,
    log,
    nativeMemRestartThresholdMb: runtimeSettings.nativeMemRestartThresholdMb,
    normalizeUserId,
    pluginEvents,
    proxyPool,
    refreshActiveTabsGauge,
    refreshTabLockQueueDepth,
    reporter,
    restartBrowser,
    routeContext,
    safeError,
    safePageClose,
    scheduleBrowserIdleShutdown,
    scheduleBrowserWarmRetry,
    sessionTimeoutMs: runtimeSettings.sessionTimeoutMs,
    sessions,
    setNativeMemBaseline: state.setNativeMemBaseline,
    setPluginContext: state.setPluginContext,
    tabInactivityMs: runtimeSettings.tabInactivityMs,
    tabLocks,
    tabsReapedTotal,
    sessionsExpiredTotal,
    validateUrl,
    withUserLimit,
  };
}
