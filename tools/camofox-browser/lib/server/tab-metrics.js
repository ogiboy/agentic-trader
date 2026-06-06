export function createTabMetrics({
  activeTabsGauge,
  pageLoadDuration,
  sessions,
}) {
  function getTotalTabCount() {
    let total = 0;
    for (const session of sessions.values()) {
      for (const group of session.tabGroups.values()) {
        total += group.size;
      }
    }
    return total;
  }

  function refreshActiveTabsGauge() {
    activeTabsGauge.set(getTotalTabCount());
  }

  async function withPageLoadDuration(action, fn) {
    const end = pageLoadDuration.startTimer();
    try {
      return await fn();
    } finally {
      end();
    }
  }

  return { getTotalTabCount, refreshActiveTabsGauge, withPageLoadDuration };
}
