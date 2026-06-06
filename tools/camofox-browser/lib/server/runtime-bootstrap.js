import { mountCamofoxRoutes } from '../routes/index.js';
import { mountRuntimeMonitors, startServerBootstrap } from './startup.js';

/**
 * Initialize the application by wiring HTTP routes, mounting runtime monitors, and bootstrapping the server.
 *
 * @param {Object} runtime - Runtime container with the app instance, route context, operational hooks, metrics, and dependencies required to mount routes/monitors and start the server (for example: app, routeContext, logging, session and browser lifecycle handlers, metrics/counters, config, plugin hooks, and validators).
 * @returns {Object} The server bootstrap result returned by startServerBootstrap.
 */
export async function startCamofoxRuntime(runtime) {
  mountCamofoxRoutes(runtime.app, runtime.routeContext);

  mountRuntimeMonitors({
    browserRestartsTotal: runtime.browserRestartsTotal,
    closeBrowserFully: runtime.closeBrowserFully,
    closeSession: runtime.closeSession,
    failuresTotal: runtime.failuresTotal,
    getBrowser: runtime.getBrowser,
    getNativeMemBaseline: runtime.getNativeMemBaseline,
    healthState: runtime.healthState,
    log: runtime.log,
    nativeMemRestartThresholdMb: runtime.nativeMemRestartThresholdMb,
    refreshActiveTabsGauge: runtime.refreshActiveTabsGauge,
    refreshTabLockQueueDepth: runtime.refreshTabLockQueueDepth,
    restartBrowser: runtime.restartBrowser,
    safePageClose: runtime.safePageClose,
    scheduleBrowserIdleShutdown: runtime.scheduleBrowserIdleShutdown,
    sessionTimeoutMs: runtime.sessionTimeoutMs,
    sessions: runtime.sessions,
    setNativeMemBaseline: runtime.setNativeMemBaseline,
    tabInactivityMs: runtime.tabInactivityMs,
    tabLocks: runtime.tabLocks,
    tabsReapedTotal: runtime.tabsReapedTotal,
    sessionsExpiredTotal: runtime.sessionsExpiredTotal,
  });

  return startServerBootstrap({
    app: runtime.app,
    authMiddleware: runtime.authMiddleware,
    closeAllSessions: runtime.closeAllSessions,
    closeBrowserFully: runtime.closeBrowserFully,
    closeSession: runtime.closeSession,
    config: runtime.config,
    destroySession: runtime.destroySession,
    ensureBrowser: runtime.ensureBrowser,
    failuresTotal: runtime.failuresTotal,
    flyMachineId: runtime.flyMachineId,
    getRegister: runtime.getRegister,
    getResourceOpts: runtime.getResourceOpts,
    getSession: runtime.getSession,
    log: runtime.log,
    normalizeUserId: runtime.normalizeUserId,
    pluginEvents: runtime.pluginEvents,
    proxyPool: runtime.proxyPool,
    refreshActiveTabsGauge: runtime.refreshActiveTabsGauge,
    refreshTabLockQueueDepth: runtime.refreshTabLockQueueDepth,
    reporter: runtime.reporter,
    safeError: runtime.safeError,
    safePageClose: runtime.safePageClose,
    scheduleBrowserIdleShutdown: runtime.scheduleBrowserIdleShutdown,
    scheduleBrowserWarmRetry: runtime.scheduleBrowserWarmRetry,
    sessions: runtime.sessions,
    setPluginContext: runtime.setPluginContext,
    validateUrl: runtime.validateUrl,
    withUserLimit: runtime.withUserLimit,
  });
}
