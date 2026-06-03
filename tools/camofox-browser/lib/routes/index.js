import { mountLegacyActionRoutes } from './legacy-actions.js';
import { mountLegacyCoreRoutes } from './legacy-core.js';
import { mountLegacySnapshotRoutes } from './legacy-snapshot.js';
import { mountSessionRoutes } from './sessions.js';
import { mountSystemRoutes } from './system.js';
import { mountTabClickRoutes } from './tabs-click.js';
import { mountTabContentRoutes } from './tabs-content.js';
import { mountTabEvaluationRoutes } from './tabs-evaluation.js';
import { mountTabHistoryRoutes } from './tabs-history.js';
import { mountTabInteractionRoutes } from './tabs-interaction.js';
import { mountTabLifecycleRoutes } from './tabs-lifecycle.js';
import { mountTabNavigationRoutes } from './tabs-navigation.js';
import { mountTabSnapshotRoutes } from './tabs-snapshot.js';
import { mountTabTypingRoutes } from './tabs-typing.js';
import { mountTraceRoutes } from './traces.js';

export function mountCamofoxRoutes(app, ctx) {
  mountSystemRoutes(app, {
    flyMachineId: ctx.flyMachineId,
    getBrowserRunning: ctx.getBrowserRunning,
    getRegister: ctx.getRegister,
    getTotalTabCount: ctx.getTotalTabCount,
    healthState: ctx.healthState,
    proxyPool: ctx.proxyPool,
    scheduleBrowserWarmRetry: ctx.scheduleBrowserWarmRetry,
    sessions: ctx.sessions,
  });

  mountTabLifecycleRoutes(app, {
    attachDownloadListener: ctx.attachDownloadListener,
    clearTabDownloads: ctx.clearTabDownloads,
    createTabState: ctx.createTabState,
    findTab: ctx.findTab,
    fly: ctx.fly,
    getSession: ctx.getSession,
    getTabGroup: ctx.getTabGroup,
    getTotalTabCount: ctx.getTotalTabCount,
    handleRouteError: ctx.handleRouteError,
    log: ctx.log,
    maxTabsGlobal: ctx.maxTabsGlobal,
    maxTabsPerSession: ctx.maxTabsPerSession,
    normalizeUserId: ctx.normalizeUserId,
    pluginEvents: ctx.pluginEvents,
    recycleOldestTab: ctx.recycleOldestTab,
    refreshActiveTabsGauge: ctx.refreshActiveTabsGauge,
    refreshTabLockQueueDepth: ctx.refreshTabLockQueueDepth,
    requestTimeoutMs: ctx.requestTimeoutMs,
    safePageClose: ctx.safePageClose,
    sessions: ctx.sessions,
    tabLocks: ctx.tabLocks,
    validateUrl: ctx.validateUrl,
    withPageLoadDuration: ctx.withPageLoadDuration,
    withTimeout: ctx.withTimeout,
  });

  mountTabNavigationRoutes(app, {
    attachDownloadListener: ctx.attachDownloadListener,
    browserRestartsTotal: ctx.browserRestartsTotal,
    buildRefs: ctx.buildRefs,
    closeSession: ctx.closeSession,
    createTabState: ctx.createTabState,
    ensureBrowser: ctx.ensureBrowser,
    expandMacro: ctx.expandMacro,
    findTab: ctx.findTab,
    getBrowserLaunchProxy: ctx.getBrowserLaunchProxy,
    getSession: ctx.getSession,
    getTabGroup: ctx.getTabGroup,
    getTotalTabCount: ctx.getTotalTabCount,
    handleRouteError: ctx.handleRouteError,
    isGoogleSearchBlocked: ctx.isGoogleSearchBlocked,
    isGoogleSearchUrl: ctx.isGoogleSearchUrl,
    isGoogleSerp: ctx.isGoogleSerp,
    log: ctx.log,
    maxTabsGlobal: ctx.maxTabsGlobal,
    maxTabsPerSession: ctx.maxTabsPerSession,
    normalizeUserId: ctx.normalizeUserId,
    pluginEvents: ctx.pluginEvents,
    proxyPool: ctx.proxyPool,
    recycleOldestTab: ctx.recycleOldestTab,
    refreshActiveTabsGauge: ctx.refreshActiveTabsGauge,
    requestTimeoutMs: ctx.requestTimeoutMs,
    safeError: ctx.safeError,
    sessions: ctx.sessions,
    validateUrl: ctx.validateUrl,
    withPageLoadDuration: ctx.withPageLoadDuration,
    withTabLock: ctx.withTabLock,
    withTimeout: ctx.withTimeout,
    withUserLimit: ctx.withUserLimit,
  });

  mountTabSnapshotRoutes(app, {
    extractGoogleSerp: ctx.extractGoogleSerp,
    findTab: ctx.findTab,
    getAriaSnapshot: ctx.getAriaSnapshot,
    handleRouteError: ctx.handleRouteError,
    interactiveRoles: ctx.interactiveRoles,
    isGoogleSearchBlocked: ctx.isGoogleSearchBlocked,
    isGoogleSearchUrl: ctx.isGoogleSearchUrl,
    isGoogleSerp: ctx.isGoogleSerp,
    isGoogleUnavailable: ctx.isGoogleUnavailable,
    log: ctx.log,
    normalizeUserId: ctx.normalizeUserId,
    pluginEvents: ctx.pluginEvents,
    proxyPool: ctx.proxyPool,
    refreshTabRefs: ctx.refreshTabRefs,
    requestTimeoutMs: ctx.requestTimeoutMs,
    rotateGoogleTab: ctx.rotateGoogleTab,
    sessions: ctx.sessions,
    skipPatterns: ctx.skipPatterns,
    snapshotBytes: ctx.snapshotBytes,
    windowSnapshot: ctx.windowSnapshot,
    withTimeout: ctx.withTimeout,
    withUserLimit: ctx.withUserLimit,
  });

  mountTabInteractionRoutes(app, {
    findTab: ctx.findTab,
    handleRouteError: ctx.handleRouteError,
    log: ctx.log,
    normalizeUserId: ctx.normalizeUserId,
    pluginEvents: ctx.pluginEvents,
    sessions: ctx.sessions,
    waitForPageReady: ctx.waitForPageReady,
    withTabLock: ctx.withTabLock,
  });

  mountTabClickRoutes(app, {
    StaleRefsError: ctx.StaleRefsError,
    findTab: ctx.findTab,
    handleRouteError: ctx.handleRouteError,
    handlerTimeoutMs: ctx.handlerTimeoutMs,
    isGoogleSerp: ctx.isGoogleSerp,
    log: ctx.log,
    normalizeUserId: ctx.normalizeUserId,
    pluginEvents: ctx.pluginEvents,
    refToLocator: ctx.refToLocator,
    refreshTabRefs: ctx.refreshTabRefs,
    safeError: ctx.safeError,
    sessions: ctx.sessions,
    withTabLock: ctx.withTabLock,
    withUserLimit: ctx.withUserLimit,
  });

  mountTabTypingRoutes(app, {
    StaleRefsError: ctx.StaleRefsError,
    findTab: ctx.findTab,
    handleRouteError: ctx.handleRouteError,
    log: ctx.log,
    normalizeUserId: ctx.normalizeUserId,
    pluginEvents: ctx.pluginEvents,
    refToLocator: ctx.refToLocator,
    refreshTabRefs: ctx.refreshTabRefs,
    safeError: ctx.safeError,
    sessions: ctx.sessions,
    withTabLock: ctx.withTabLock,
  });

  mountTabHistoryRoutes(app, {
    buildRefs: ctx.buildRefs,
    findTab: ctx.findTab,
    handleRouteError: ctx.handleRouteError,
    log: ctx.log,
    normalizeUserId: ctx.normalizeUserId,
    sessions: ctx.sessions,
    withTabLock: ctx.withTabLock,
  });

  mountTabContentRoutes(app, {
    classifyError: ctx.classifyError,
    failuresTotal: ctx.failuresTotal,
    findTab: ctx.findTab,
    handleRouteError: ctx.handleRouteError,
    log: ctx.log,
    normalizeUserId: ctx.normalizeUserId,
    pluginEvents: ctx.pluginEvents,
    safeError: ctx.safeError,
    sessions: ctx.sessions,
  });

  mountTabEvaluationRoutes(app, {
    classifyError: ctx.classifyError,
    failuresTotal: ctx.failuresTotal,
    findTab: ctx.findTab,
    log: ctx.log,
    normalizeUserId: ctx.normalizeUserId,
    pluginEvents: ctx.pluginEvents,
    safeError: ctx.safeError,
    sessions: ctx.sessions,
  });

  mountTraceRoutes(app, {
    authMiddleware: ctx.authMiddleware,
    log: ctx.log,
    normalizeUserId: ctx.normalizeUserId,
    tracesDir: ctx.tracesDir,
  });

  mountSessionRoutes(app, {
    closeSession: ctx.closeSession,
    config: ctx.config,
    failuresTotal: ctx.failuresTotal,
    getSession: ctx.getSession,
    handleRouteError: ctx.handleRouteError,
    log: ctx.log,
    normalizeUserId: ctx.normalizeUserId,
    pluginEvents: ctx.pluginEvents,
    safeError: ctx.safeError,
    scheduleBrowserIdleShutdown: ctx.scheduleBrowserIdleShutdown,
    sessions: ctx.sessions,
  });

  mountLegacyCoreRoutes(app, {
    attachDownloadListener: ctx.attachDownloadListener,
    buildRefs: ctx.buildRefs,
    closeAllSessions: ctx.closeAllSessions,
    closeBrowserFully: ctx.closeBrowserFully,
    config: ctx.config,
    createTabState: ctx.createTabState,
    ensureBrowser: ctx.ensureBrowser,
    failuresTotal: ctx.failuresTotal,
    findTab: ctx.findTab,
    fly: ctx.fly,
    getBrowser: ctx.getBrowser,
    getSession: ctx.getSession,
    getTabGroup: ctx.getTabGroup,
    getTotalTabCount: ctx.getTotalTabCount,
    handleRouteError: ctx.handleRouteError,
    isGoogleSerp: ctx.isGoogleSerp,
    log: ctx.log,
    maxTabsGlobal: ctx.maxTabsGlobal,
    maxTabsPerSession: ctx.maxTabsPerSession,
    normalizeUserId: ctx.normalizeUserId,
    pluginEvents: ctx.pluginEvents,
    recycleOldestTab: ctx.recycleOldestTab,
    refreshActiveTabsGauge: ctx.refreshActiveTabsGauge,
    safeError: ctx.safeError,
    sessions: ctx.sessions,
    timingSafeCompare: ctx.timingSafeCompare,
    validateUrl: ctx.validateUrl,
    withPageLoadDuration: ctx.withPageLoadDuration,
    withTabLock: ctx.withTabLock,
  });

  mountLegacySnapshotRoutes(app, {
    buildRefs: ctx.buildRefs,
    extractGoogleSerp: ctx.extractGoogleSerp,
    findTab: ctx.findTab,
    getAriaSnapshot: ctx.getAriaSnapshot,
    handleRouteError: ctx.handleRouteError,
    isGoogleSerp: ctx.isGoogleSerp,
    log: ctx.log,
    normalizeUserId: ctx.normalizeUserId,
    sessions: ctx.sessions,
    snapshotBytes: ctx.snapshotBytes,
    windowSnapshot: ctx.windowSnapshot,
  });

  mountLegacyActionRoutes(app, {
    StaleRefsError: ctx.StaleRefsError,
    buildRefs: ctx.buildRefs,
    findTab: ctx.findTab,
    handleRouteError: ctx.handleRouteError,
    log: ctx.log,
    normalizeUserId: ctx.normalizeUserId,
    refToLocator: ctx.refToLocator,
    safePageClose: ctx.safePageClose,
    sessions: ctx.sessions,
    tabLocks: ctx.tabLocks,
    withTabLock: ctx.withTabLock,
  });
}
