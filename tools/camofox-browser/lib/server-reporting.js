import fs from 'node:fs';
import { createReporter } from './reporter.js';

export function createServerReporting({ config, getBrowser, sessions }) {
  const pkgVersion = (() => {
    try {
      return JSON.parse(
        fs.readFileSync(new URL('../package.json', import.meta.url), 'utf8'),
      ).version;
    } catch {
      return 'unknown';
    }
  })();
  const reporter = createReporter({ ...config, version: pkgVersion });

  function countTabs() {
    let total = 0;
    for (const session of sessions.values()) {
      for (const group of session.tabGroups.values()) total += group.size;
    }
    return total;
  }

  function browserPid() {
    try {
      return getBrowser()?.process?.()?.pid ?? null;
    } catch {
      return null;
    }
  }

  function getResourceOpts() {
    return {
      sessionCount: sessions.size,
      tabCount: countTabs(),
      browserPid: browserPid(),
    };
  }

  reporter.startWatchdog(30_000, () => {
    const summary = [];
    for (const [sid, session] of sessions) {
      const tabUrls = [];
      for (const [, group] of session.tabGroups) {
        for (const [, tab] of group) {
          try {
            const url = tab.page?.url?.() || 'unknown';
            tabUrls.push(url);
          } catch {
            tabUrls.push('error');
          }
        }
      }
      if (tabUrls.length > 0)
        summary.push({ session: sid, tabs: tabUrls.length, urls: tabUrls });
    }
    return { resourceOpts: getResourceOpts(), sessions: summary.length, summary };
  });

  return { getResourceOpts, reporter };
}
