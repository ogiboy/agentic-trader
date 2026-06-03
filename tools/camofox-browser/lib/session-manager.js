import crypto from 'node:crypto';

export function createSessionManager({
  clearSessionDownloads,
  clearSessionLocks,
  coalesceInflight,
  config,
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
}) {
  const sessionCreations = new Map();

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
      await closeSession(userId, session, {
        reason,
        clearDownloads,
        clearLocks,
      });
    }
  }

  async function getSession(userId, { trace = false } = {}) {
    const key = normalizeUserId(userId);
    let session = sessions.get(key);

    if (session) {
      if (session._closing) {
        session = null;
      } else {
        try {
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
        if (sessions.size >= config.maxSessions) {
          throw new Error('Maximum concurrent sessions reached');
        }
        const b = await ensureBrowser();
        const contextOptions = {
          viewport: { width: 1280, height: 720 },
          permissions: ['geolocation'],
        };
        if (!config.proxy.host) {
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
          const traceDir = ensureTracesDir(config.tracesDir, key);
          tracePath = tracePathFor(config.tracesDir, key, makeTraceFilename());
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
        await pluginEvents.emitAsync('session:created', {
          userId: key,
          context,
        });
        const launchProxy = getBrowserLaunchProxy();
        log('info', 'session created', {
          userId: key,
          proxyMode: proxyPool?.mode || null,
          proxyServer: sessionProxy?.server || launchProxy?.server || null,
          proxySession: sessionProxy?.sessionId || launchProxy?.sessionId || null,
        });
        return created;
      });
    }
    session.lastAccess = Date.now();
    return session;
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

  return { closeAllSessions, closeSession, destroySession, getSession };
}
