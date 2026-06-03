export const INTERACTIVE_ROLES = [
  'button',
  'link',
  'textbox',
  'checkbox',
  'radio',
  'menuitem',
  'tab',
  'searchbox',
  'slider',
  'spinbutton',
  'switch',
];

export const SKIP_PATTERNS = [/date/i, /calendar/i, /picker/i, /datepicker/i];

export class StaleRefsError extends Error {
  constructor(ref, maxRef, totalRefs) {
    super(
      `Unknown ref: ${ref} (valid refs: e1-${maxRef}, ${totalRefs} total). Refs reset after navigation - call snapshot first.`,
    );
    this.name = 'StaleRefsError';
    this.code = 'stale_refs';
    this.ref = ref;
  }
}

export function createRefHelpers(ctx) {
  const refreshReadyTimeoutMs = 2500;

  async function buildRefs(page) {
    const refs = new Map();

    if (!page || page.isClosed()) {
      ctx.log('warn', 'buildRefs: page closed or invalid');
      return refs;
    }

    if (ctx.isGoogleSerp(page.url())) {
      const { refs: googleRefs } = await ctx.extractGoogleSerp(page);
      return googleRefs;
    }

    const start = Date.now();
    let timerId;
    const timeoutPromise = new Promise((_, reject) => {
      timerId = setTimeout(
        () => reject(new Error('buildRefs_timeout')),
        ctx.buildrefsTimeoutMs,
      );
    });

    try {
      const result = await Promise.race([
        buildRefsInner(page, refs, start),
        timeoutPromise,
      ]);
      clearTimeout(timerId);
      return result;
    } catch (err) {
      clearTimeout(timerId);
      if (err.message === 'buildRefs_timeout') {
        ctx.log('warn', 'buildRefs: total timeout exceeded', {
          elapsed: Date.now() - start,
        });
        return refs;
      }
      throw err;
    }
  }

  async function buildRefsInner(page, refs, start) {
    await ctx.waitForPageReady(page, {
      timeout: refreshReadyTimeoutMs,
      waitForNetwork: false,
      waitForHydration: false,
      settleMs: 100,
    });

    const elapsed = Date.now() - start;
    const remaining = ctx.buildrefsTimeoutMs - elapsed;
    if (remaining < 2000) {
      ctx.log('warn', 'buildRefs: insufficient time for ariaSnapshot', {
        elapsed,
      });
      return refs;
    }

    let ariaYaml;
    try {
      ariaYaml = await page
        .locator('body')
        .ariaSnapshot({ timeout: Math.min(remaining - 1000, 5000) });
    } catch {
      ctx.log('warn', 'ariaSnapshot failed, retrying');
      const retryBudget = ctx.buildrefsTimeoutMs - (Date.now() - start);
      if (retryBudget < 2000) return refs;
      try {
        ariaYaml = await page
          .locator('body')
          .ariaSnapshot({ timeout: Math.min(retryBudget - 500, 5000) });
      } catch (retryErr) {
        ctx.log('warn', 'ariaSnapshot retry failed, returning empty refs', {
          error: retryErr.message,
        });
        return refs;
      }
    }

    if (!ariaYaml) {
      ctx.log('warn', 'buildRefs: no aria snapshot');
      return refs;
    }

    const seenCounts = new Map();
    let refCounter = 1;
    for (const line of ariaYaml.split('\n')) {
      if (refCounter > ctx.maxSnapshotNodes) break;

      const match = line.match(/^\s*-\s+(\w+)(?:\s+"([^"]*)")?/);
      if (!match) continue;

      const [, role, name] = match;
      const normalizedRole = role.toLowerCase();
      if (normalizedRole === 'combobox') continue;
      if (name && SKIP_PATTERNS.some((pattern) => pattern.test(name))) {
        continue;
      }
      if (!INTERACTIVE_ROLES.includes(normalizedRole)) continue;

      const normalizedName = name || '';
      const key = `${normalizedRole}:${normalizedName}`;
      const nth = seenCounts.get(key) || 0;
      seenCounts.set(key, nth + 1);

      refs.set(`e${refCounter++}`, {
        role: normalizedRole,
        name: normalizedName,
        nth,
      });
    }

    return refs;
  }

  async function getAriaSnapshot(page) {
    if (!page || page.isClosed()) return null;
    await ctx.waitForPageReady(page, {
      timeout: refreshReadyTimeoutMs,
      waitForNetwork: false,
      waitForHydration: false,
      settleMs: 100,
    });
    try {
      return await page.locator('body').ariaSnapshot({ timeout: 5000 });
    } catch (err) {
      ctx.log('warn', 'getAriaSnapshot failed', { error: err.message });
      return null;
    }
  }

  function refToLocator(page, ref, refs) {
    const info = refs.get(ref);
    if (!info) return null;

    const { role, name, nth } = info;
    return page.getByRole(role, name ? { name } : undefined).nth(nth);
  }

  async function refreshTabRefs(tabState, options = {}) {
    const {
      reason = 'refresh',
      timeoutMs = null,
      preserveExistingOnEmpty = true,
    } = options;

    const beforeUrl = tabState.page?.url?.() || '';
    const existingRefs =
      tabState.refs instanceof Map ? tabState.refs : new Map();
    const refreshPromise = buildRefs(tabState.page);

    const refreshedRefs = timeoutMs
      ? await Promise.race([
          refreshPromise,
          new Promise((_, reject) =>
            setTimeout(
              () => reject(new Error(`${reason}_refs_timeout`)),
              timeoutMs,
            ),
          ),
        ])
      : await refreshPromise;

    const afterUrl = tabState.page?.url?.() || beforeUrl;
    if (
      preserveExistingOnEmpty &&
      refreshedRefs.size === 0 &&
      existingRefs.size > 0 &&
      beforeUrl === afterUrl
    ) {
      ctx.log('warn', 'preserving previous refs after empty rebuild', {
        reason,
        url: afterUrl,
        previousRefs: existingRefs.size,
      });
      return existingRefs;
    }

    return refreshedRefs;
  }

  return { buildRefs, getAriaSnapshot, refToLocator, refreshTabRefs };
}
