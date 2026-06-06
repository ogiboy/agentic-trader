export function createRuntimeSettings(config) {
  return {
    buildrefsTimeoutMs: config.buildrefsTimeoutMs,
    failureThreshold: 3,
    handlerTimeoutMs: config.handlerTimeoutMs,
    maxConsecutiveTimeouts: 3,
    maxSnapshotNodes: 500,
    maxTabsGlobal: config.maxTabsGlobal,
    maxTabsPerSession: config.maxTabsPerSession,
    nativeMemRestartThresholdMb: config.nativeMemRestartThresholdMb,
    pageCloseTimeoutMs: 5000,
    sessionTimeoutMs: config.sessionTimeoutMs,
    tabInactivityMs: config.tabInactivityMs,
  };
}

export function createHealthState() {
  return {
    consecutiveNavFailures: 0,
    lastSuccessfulNav: Date.now(),
    isRecovering: false,
    activeOps: 0,
  };
}

export function createRequestTimeoutMs({ handlerTimeoutMs, proxyPool }) {
  return function requestTimeoutMs(baseMs = handlerTimeoutMs) {
    return proxyPool?.canRotateSessions ? Math.max(baseMs, 180000) : baseMs;
  };
}

export function logProxyPool({ config, log, proxyPool }) {
  if (!proxyPool) {
    log('info', 'no proxy configured');
    return;
  }
  log('info', 'proxy pool created', {
    mode: proxyPool.mode,
    host: proxyPool.canRotateSessions
      ? config.proxy.backconnectHost
      : config.proxy.host,
    ports: proxyPool.canRotateSessions
      ? [config.proxy.backconnectPort]
      : config.proxy.ports,
    poolSize: proxyPool.size,
    country: config.proxy.country || null,
    state: config.proxy.state || null,
    city: config.proxy.city || null,
  });
}
