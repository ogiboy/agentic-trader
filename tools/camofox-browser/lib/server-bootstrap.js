import { VirtualDisplay } from 'camoufox-js/dist/virtdisplay.js';
import os from 'node:os';
import { isLoopbackAddress } from './auth.js';
import { createMetric, startMemoryReporter, stopMemoryReporter } from './metrics.js';
import { mountDocs } from './openapi.js';
import { loadPlugins } from './plugins.js';
import { buildProxyUrl } from './proxy.js';
import {
  cleanupOrphanedTempFiles,
  cleanupStaleFirefoxProfiles,
} from './tmp-cleanup.js';
import { sweepOldTraces } from './tracing.js';

export async function startCamofoxServer({
  app,
  authMiddleware,
  closeAllSessions,
  closeBrowserFully,
  closeSession,
  config,
  destroySession,
  ensureBrowser,
  failuresTotal,
  flyMachineId,
  getSession,
  getRegister,
  log,
  normalizeUserId,
  pluginEvents,
  proxyPool,
  refreshActiveTabsGauge,
  refreshTabLockQueueDepth,
  reporter,
  getResourceOpts,
  safeError,
  safePageClose,
  scheduleBrowserIdleShutdown,
  scheduleBrowserWarmRetry,
  sessions,
  setPluginContext,
  validateUrl,
  withUserLimit,
}) {
  let server = null;
  let shuttingDown = false;

  process.on('uncaughtException', (err) => {
    pluginEvents.emit('browser:error', { error: err });
    log('error', 'uncaughtException', { error: err.message, stack: err.stack });
    reporter?.reportCrash?.(err, { resourceOpts: getResourceOpts?.() });
    process.exit(1);
  });
  process.on('unhandledRejection', (reason) => {
    log('error', 'unhandledRejection', { reason: String(reason) });
  });

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

    server?.close();
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

  const port = config.port;
  const host = config.host || '127.0.0.1';
  if (config.nodeEnv === 'production' && !config.accessKey) {
    throw new Error('CAMOFOX_ACCESS_KEY is required when NODE_ENV=production');
  }
  if (!isLoopbackAddress(host) && !config.accessKey) {
    throw new Error(
      'CAMOFOX_ACCESS_KEY is required when CAMOFOX_HOST is not loopback',
    );
  }
  pluginEvents.emit('server:starting', { host, port });

  const pluginCtx = {
    sessions,
    config,
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
    createVirtualDisplay: () => new VirtualDisplay(),
    VirtualDisplay,
  };
  setPluginContext(pluginCtx);
  const loadedPlugins = await loadPlugins(app, pluginCtx);
  mountDocs(app);

  server = app.listen(port, host, async () => {
    startMemoryReporter();
    refreshActiveTabsGauge();
    refreshTabLockQueueDepth();
    pluginEvents.emit('server:started', {
      host,
      port,
      pid: process.pid,
      plugins: loadedPlugins,
    });
    log('info', flyMachineId ? 'server started (fly)' : 'server started', {
      host,
      port,
      pid: process.pid,
      ...(flyMachineId ? { machineId: flyMachineId } : {}),
      nodeVersion: process.version,
    });

    const tmpCleanup = cleanupOrphanedTempFiles({ tmpDir: os.tmpdir() });
    if (tmpCleanup.removed > 0) {
      log('info', 'cleaned up orphaned camoufox temp files', tmpCleanup);
    }
    const profileCleanup = cleanupStaleFirefoxProfiles();
    if (profileCleanup.removed > 0) {
      log('info', 'cleaned up stale firefox profiles on startup', profileCleanup);
    }
    setInterval(
      () => {
        try {
          const cleaned = cleanupStaleFirefoxProfiles();
          if (cleaned.removed > 0) {
            log('info', 'periodic firefox profile cleanup', cleaned);
          }
        } catch {
          // Best effort.
        }
      },
      10 * 60 * 1000,
    ).unref();

    const traceSweep = sweepOldTraces({
      baseDir: config.tracesDir,
      ttlMs: config.tracesTtlHours * 3600 * 1000,
      maxBytesPerFile: config.tracesMaxBytes,
    });
    if (traceSweep.removedTtl > 0 || traceSweep.removedOversized > 0) {
      log('info', 'swept old traces', traceSweep);
    }
    if (config.browserPrewarmEnabled) {
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
  });

  server.on('error', (err) => {
    if (err.code === 'EADDRINUSE') {
      log('error', 'port in use', { port });
      process.exit(1);
    }
    log('error', 'server error', { error: err.message });
    process.exit(1);
  });

  return { loadedPlugins, pluginCtx, server };
}
