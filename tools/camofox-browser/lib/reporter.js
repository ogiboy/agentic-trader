// Local-first reporter facade for Agentic Trader's Camofox helper.
//
// The upstream project ships a remote crash/hang reporter. Agentic Trader keeps
// this helper fully local: browser health can be inspected from local logs and
// `/health`, while reporter calls are safe no-ops with no network side effects.

import { classifyProxyError, collectResourceSnapshot } from './resources.js';

export { classifyProxyError, collectResourceSnapshot };

export function createTabHealthTracker(page) {
  const health = {
    crashes: 0,
    pageErrors: 0,
    requestFailures: 0,
    inflightRequests: 0,
    maxRedirectDepth: 0,
    redirectStatusCodes: [],
    statusCounts: {},
    botDetection: null,
    lastNavResponseSize: 0,
    _redirectDepth: 0,
  };

  if (!page || typeof page.on !== 'function') {
    return {
      health,
      snapshot: () => ({ ...health, _redirectDepth: undefined }),
      getReadyState: async () => null,
    };
  }

  page.on('crash', () => { health.crashes += 1; });
  page.on('pageerror', () => { health.pageErrors += 1; });
  page.on('requestfailed', () => {
    health.requestFailures += 1;
    health.inflightRequests = Math.max(0, health.inflightRequests - 1);
  });
  page.on('request', (request) => {
    health.inflightRequests += 1;
    if (request.isNavigationRequest?.()) {
      if (request.redirectedFrom?.()) {
        health._redirectDepth += 1;
        health.maxRedirectDepth = Math.max(health.maxRedirectDepth, health._redirectDepth);
      } else {
        health._redirectDepth = 0;
        health.redirectStatusCodes = [];
        health.inflightRequests = 0;
      }
    }
  });
  page.on('requestfinished', () => {
    health.inflightRequests = Math.max(0, health.inflightRequests - 1);
  });
  page.on('response', (response) => {
    try {
      const status = response.status();
      if (status >= 400) health.statusCounts[status] = (health.statusCounts[status] || 0) + 1;
      const request = response.request?.();
      if (request?.isNavigationRequest?.()) {
        health.redirectStatusCodes.push(status);
        const contentLength = response.headers?.()['content-length'];
        if (contentLength) health.lastNavResponseSize = parseInt(contentLength, 10) || 0;
      }
    } catch {
      // The page may have closed while Playwright was emitting the event.
    }
  });
  page.on('dialog', async (dialog) => {
    try {
      await dialog.dismiss();
    } catch {
      // Page may already be closed.
    }
  });

  return {
    health,
    snapshot: () => {
      const { _redirectDepth: _ignored, ...publicHealth } = health;
      return { ...publicHealth };
    },
    getReadyState: async () => {
      try {
        return await Promise.race([
          page.evaluate(() => document.readyState),
          new Promise((resolve) => setTimeout(() => resolve('unresponsive'), 1000)),
        ]);
      } catch {
        return 'unresponsive';
      }
    },
  };
}

export function createReporter() {
  return {
    reportCrash: async () => {},
    reportHang: async () => {},
    reportFeedback: async () => {},
    startWatchdog: () => {},
    trackRoute: () => {},
    resetNativeMemBaseline: () => {},
  };
}
