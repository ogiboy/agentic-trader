export function startRuntimeMonitors({
  browserRestartsTotal,
  closeBrowserFully,
  closeSession,
  failuresTotal,
  getBrowser,
  getNativeMemBaseline,
  healthState,
  log,
  nativeMemRestartThresholdMb,
  refreshActiveTabsGauge,
  refreshTabLockQueueDepth,
  restartBrowser,
  safePageClose,
  scheduleBrowserIdleShutdown,
  sessionTimeoutMs,
  sessions,
  setNativeMemBaseline,
  tabInactivityMs,
  tabLocks,
  tabsReapedTotal,
  sessionsExpiredTotal,
}) {
  setInterval(() => {
    const now = Date.now();
    for (const [userId, session] of Array.from(sessions.entries())) {
      if (now - session.lastAccess > sessionTimeoutMs) {
        session._closing = true;
        const idleMs = now - session.lastAccess;
        sessionsExpiredTotal.inc();
        closeSession(userId, session, {
          reason: 'session_timeout',
          clearDownloads: true,
          clearLocks: true,
        }).catch(() => {});
        log('info', 'session expired', { userId, idleMs });
      }
    }
    if (sessions.size === 0) {
      scheduleBrowserIdleShutdown();
    }
    refreshTabLockQueueDepth();
  }, 60_000);

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
            if (idleMs >= tabInactivityMs) {
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
              const lock = tabLocks.get(tabId);
              if (lock) lock.drain();
              tabLocks.delete(tabId);
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

  setInterval(() => {
    const browser = getBrowser();
    if (sessions.size > 0 || !browser) return;
    const mem = process.memoryUsage();
    const nativeMemMb = Math.round((mem.rss - mem.heapUsed) / 1048576);
    if (getNativeMemBaseline() === null) {
      setNativeMemBaseline(nativeMemMb);
      return;
    }
    const growth = nativeMemMb - getNativeMemBaseline();
    if (growth >= nativeMemRestartThresholdMb) {
      log('warn', 'native memory pressure, restarting browser', {
        baselineMb: getNativeMemBaseline(),
        currentMb: nativeMemMb,
        growthMb: growth,
        thresholdMb: nativeMemRestartThresholdMb,
      });
      browserRestartsTotal.labels('memory_pressure').inc();
      closeBrowserFully('memory_pressure').catch((err) => {
        log('error', 'memory pressure browser close failed', {
          error: err.message,
        });
      });
    }
  }, 30_000);

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
      browserConnected: getBrowser()?.isConnected() ?? false,
    });
  }, 5 * 60_000);

  setInterval(async () => {
    const browser = getBrowser();
    if (!browser || healthState.isRecovering) return;
    const timeSinceSuccess = Date.now() - healthState.lastSuccessfulNav;
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
      restartBrowser('health probe failed', healthState).catch(() => {});
    }
  }, 60_000);
}
