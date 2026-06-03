export function createTabStateManager({
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
}) {
  function getTabGroup(session, listItemId) {
    let group = session.tabGroups.get(listItemId);
    if (!group) {
      group = new Map();
      session.tabGroups.set(listItemId, group);
    }
    return group;
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

    browserRestartsTotal.labels(reason).inc();

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

  return {
    createTabState,
    destroyTab,
    findTab,
    getTabGroup,
    isGoogleUnavailable,
    recycleOldestTab,
    rotateGoogleTab,
  };
}
