export function createRouteErrorHandler({
  actionFromReq,
  browserRestartsTotal,
  classifyError,
  classifyProxyError,
  config,
  destroySession,
  destroyTab,
  failuresTotal,
  findTab,
  getResourceOpts,
  log,
  maxConsecutiveTimeouts,
  normalizeUserId,
  pluginEvents,
  proxyPool,
  reporter,
  sendError,
  sessions,
}) {
  function isDeadContextError(err) {
    const msg = err?.message || '';
    return (
      msg.includes('Target page, context or browser has been closed') ||
      msg.includes('browser has been closed') ||
      msg.includes('Context closed') ||
      msg.includes('Browser closed')
    );
  }

  function isTimeoutError(err) {
    const msg = err?.message || '';
    return (
      msg.includes('timed out after') ||
      (msg.includes('Timeout') && msg.includes('exceeded'))
    );
  }

  function isTabLockQueueTimeout(err) {
    return err?.message === 'Tab lock queue timeout';
  }

  function isTabDestroyedError(err) {
    return err?.message === 'Tab destroyed';
  }

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
    if (userId && isTimeoutError(err)) {
      const session = sessions.get(normalizeUserId(userId));
      if (session && tabId) {
        const found = findTab(session, tabId);
        if (found) {
          found.tabState.consecutiveTimeouts++;
          if (found.tabState.consecutiveTimeouts >= maxConsecutiveTimeouts) {
            log('warn', 'auto-destroying tab after consecutive timeouts', {
              tabId,
              count: found.tabState.consecutiveTimeouts,
            });
            destroyTab(session, tabId, 'consecutive_timeouts', userId);
          }
        }
      }
    }
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
    if (isTabDestroyedError(err)) {
      return res
        .status(410)
        .json({ error: 'Tab was destroyed. Open a new tab.', ...extraFields });
    }

    const frustrationTypes = new Set(['timeout', 'dead_context', 'nav_aborted']);
    if (frustrationTypes.has(failureType) && userId && tabId) {
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
          const proxyErr = classifyProxyError(err?.message);
          reporter.reportHang(
            action,
            req.startTime ? Date.now() - req.startTime : 0,
            {
              error: err,
              healthSnapshot: ts.healthTracker
                ? ts.healthTracker.snapshot()
                : undefined,
              healthTracker: ts.healthTracker || null,
              resourceOpts: getResourceOpts(),
              proxy: proxyPool
                ? {
                    configured: true,
                    type: proxyPool.mode || null,
                    authConfigured: !!config.proxy?.username,
                    error: proxyErr.proxyError,
                    tlsError: proxyErr.proxyTlsError,
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

  return {
    handleRouteError,
    isDeadContextError,
    isProxyError,
    isTabDestroyedError,
    isTabLockQueueTimeout,
    isTimeoutError,
  };
}
