import { launchOptions } from 'camoufox-js';
import crypto from 'node:crypto';
import os from 'node:os';
import { firefox } from 'playwright-core';

export function createBrowserLifecycle({
  browserRestartsTotal,
  closeAllSessions,
  closeBrowserFully,
  config,
  createVirtualDisplay,
  failuresTotal,
  getBrowser,
  getHostOS,
  isGoogleSearchBlocked,
  isGoogleSerp,
  log,
  normalizePlaywrightProxy,
  pluginEvents,
  proxyPool,
  sessions,
  setBrowser,
  setLastBrowserPid,
}) {
  const browserIdleTimeoutMs = config.browserIdleTimeoutMs;
  let browserIdleTimer = null;
  let browserLaunchPromise = null;
  let browserWarmRetryTimer = null;
  let virtualDisplay = null;
  let browserLaunchProxy = null;

  function scheduleBrowserIdleShutdown() {
    clearBrowserIdleTimer();
    if (sessions.size === 0 && getBrowser()) {
      browserIdleTimer = setTimeout(async () => {
        if (sessions.size === 0 && getBrowser()) {
          log('info', 'browser idle shutdown (no sessions)');
          await closeBrowserFully('idle_shutdown');
        }
      }, browserIdleTimeoutMs);
    }
  }

  function clearBrowserIdleTimer() {
    if (browserIdleTimer) {
      clearTimeout(browserIdleTimer);
      browserIdleTimer = null;
    }
  }

  function scheduleBrowserWarmRetry(delayMs = 5000) {
    if (!config.browserPrewarmEnabled) return;
    if (browserWarmRetryTimer || getBrowser() || browserLaunchPromise) return;
    browserWarmRetryTimer = setTimeout(async () => {
      browserWarmRetryTimer = null;
      try {
        const start = Date.now();
        await ensureBrowser();
        log('info', 'background browser warm retry succeeded', {
          ms: Date.now() - start,
        });
      } catch (err) {
        log('warn', 'background browser warm retry failed', {
          error: err.message,
          nextDelayMs: delayMs,
        });
        scheduleBrowserWarmRetry(Math.min(delayMs * 2, 30000));
      }
    }, delayMs);
  }

  async function restartBrowser(reason, healthState) {
    if (healthState.isRecovering) return;
    healthState.isRecovering = true;
    browserRestartsTotal.labels(reason).inc();
    log('error', 'restarting browser', {
      reason,
      failures: healthState.consecutiveNavFailures,
    });
    pluginEvents.emit('browser:restart', { reason });
    try {
      await closeAllSessions(`browser_restart:${reason}`, {
        clearDownloads: true,
        clearLocks: true,
      });
      await closeBrowserFully(`browser_restart:${reason}`);
      pluginEvents.emit('browser:closed', { reason });
      browserLaunchPromise = null;
      await ensureBrowser();
      healthState.consecutiveNavFailures = 0;
      healthState.lastSuccessfulNav = Date.now();
      log('info', 'browser restarted successfully');
    } catch (err) {
      log('error', 'browser restart failed', { error: err.message });
    } finally {
      healthState.isRecovering = false;
    }
  }

  async function probeGoogleSearch(candidateBrowser) {
    let context = null;
    try {
      context = await candidateBrowser.newContext({
        viewport: { width: 1280, height: 720 },
        permissions: ['geolocation'],
      });
      const page = await context.newPage();
      await page.goto('https://www.google.com/', {
        waitUntil: 'domcontentloaded',
        timeout: 30000,
      });
      await page.waitForTimeout(1200);
      await page.goto('https://www.google.com/search?q=weather%20today', {
        waitUntil: 'domcontentloaded',
        timeout: 30000,
      });
      await page.waitForTimeout(4000);

      const blocked = await isGoogleSearchBlocked(page);
      return {
        ok: !blocked && isGoogleSerp(page.url()),
        url: page.url(),
        blocked,
      };
    } finally {
      await context?.close().catch(() => {});
    }
  }

  function attachBrowserCleanup(candidateBrowser, localVirtualDisplay) {
    const origClose = candidateBrowser.close.bind(candidateBrowser);
    candidateBrowser.close = async (...args) => {
      await origClose(...args);
      browserLaunchProxy = null;
      if (localVirtualDisplay) {
        localVirtualDisplay.kill();
        if (virtualDisplay === localVirtualDisplay) virtualDisplay = null;
      }
    };
  }

  async function launchBrowserInstance() {
    const hostOS = getHostOS();
    const maxAttempts = proxyPool?.launchRetries ?? 1;
    let lastError = null;

    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      const launchProxy = proxyPool
        ? proxyPool.getLaunchProxy(
            proxyPool.canRotateSessions
              ? `browser-${crypto.randomUUID().replace(/-/g, '').slice(0, 12)}`
              : undefined,
          )
        : null;

      let localVirtualDisplay = null;
      let vdDisplay = undefined;
      let candidateBrowser = null;

      try {
        if (os.platform() === 'linux') {
          localVirtualDisplay = createVirtualDisplay();
          vdDisplay = localVirtualDisplay.get();
          log('info', 'xvfb virtual display started', {
            display: vdDisplay,
            attempt,
          });
        }
      } catch (err) {
        log('warn', 'xvfb not available, falling back to headless', {
          error: err.message,
          attempt,
        });
        localVirtualDisplay = null;
      }

      const useVirtualDisplay = !!vdDisplay;
      log('info', 'launching camoufox', {
        hostOS,
        attempt,
        maxAttempts,
        geoip: !!launchProxy,
        proxyMode: proxyPool?.mode || null,
        proxyServer: launchProxy?.server || null,
        proxySession: launchProxy?.sessionId || null,
        proxyPoolSize: proxyPool?.size || 0,
        virtualDisplay: useVirtualDisplay,
      });

      try {
        const options = await launchOptions({
          headless: useVirtualDisplay ? false : true,
          os: hostOS,
          humanize: true,
          enable_cache: true,
          proxy: launchProxy,
          geoip: !!launchProxy,
          virtual_display: vdDisplay,
        });
        options.proxy = normalizePlaywrightProxy(options.proxy);
        await pluginEvents.emitAsync('browser:launching', { options });

        candidateBrowser = await firefox.launch(options);

        if (proxyPool?.canRotateSessions) {
          const probe = await probeGoogleSearch(candidateBrowser);
          if (!probe.ok) {
            log('warn', 'browser launch google probe failed', {
              attempt,
              maxAttempts,
              proxySession: launchProxy?.sessionId || null,
              url: probe.url,
            });
            if (attempt < maxAttempts) {
              await candidateBrowser.close().catch(() => {});
              if (localVirtualDisplay) localVirtualDisplay.kill();
              continue;
            }
            log(
              'error',
              'all proxy sessions Google-blocked, accepting browser in degraded mode',
              {
                maxAttempts,
                proxySession: launchProxy?.sessionId || null,
              },
            );
          }
        }

        virtualDisplay = localVirtualDisplay;
        browserLaunchProxy = launchProxy;
        setLastBrowserPid(candidateBrowser.process?.()?.pid ?? null);
        setBrowser(candidateBrowser);
        attachBrowserCleanup(candidateBrowser, localVirtualDisplay);
        pluginEvents.emit('browser:launched', {
          browser: candidateBrowser,
          display: vdDisplay,
        });

        log('info', 'camoufox launched', {
          attempt,
          maxAttempts,
          virtualDisplay: useVirtualDisplay,
          proxyMode: proxyPool?.mode || null,
          proxyServer: launchProxy?.server || null,
          proxySession: launchProxy?.sessionId || null,
        });
        return candidateBrowser;
      } catch (err) {
        lastError = err;
        log('warn', 'camoufox launch attempt failed', {
          attempt,
          maxAttempts,
          error: err.message,
          proxySession: launchProxy?.sessionId || null,
        });
        await candidateBrowser?.close().catch(() => {});
        if (localVirtualDisplay) localVirtualDisplay.kill();
      }
    }

    throw lastError || new Error('Failed to launch a usable browser');
  }

  async function ensureBrowser() {
    clearBrowserIdleTimer();
    const currentBrowser = getBrowser();
    if (currentBrowser && !currentBrowser.isConnected()) {
      failuresTotal.labels('browser_disconnected', 'internal').inc();
      log('warn', 'browser disconnected, clearing dead sessions and relaunching', {
        deadSessions: sessions.size,
      });
      await closeAllSessions('browser_disconnected', {
        clearDownloads: true,
        clearLocks: true,
      });
      await closeBrowserFully('browser_disconnected');
    }
    if (getBrowser()) return getBrowser();
    if (browserLaunchPromise) return browserLaunchPromise;
    const launchTimeoutMs = proxyPool?.launchTimeoutMs ?? 60000;
    browserLaunchPromise = Promise.race([
      launchBrowserInstance(),
      new Promise((_, reject) =>
        setTimeout(
          () =>
            reject(
              new Error(
                `Browser launch timeout (${Math.round(launchTimeoutMs / 1000)}s)`,
              ),
            ),
          launchTimeoutMs,
        ),
      ),
    ]).finally(() => {
      browserLaunchPromise = null;
    });
    return browserLaunchPromise;
  }

  return {
    ensureBrowser,
    getBrowserLaunchProxy: () => browserLaunchProxy,
    restartBrowser,
    scheduleBrowserIdleShutdown,
    scheduleBrowserWarmRetry,
  };
}
