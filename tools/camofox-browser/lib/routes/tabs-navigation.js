async function ensureTabForNavigation(req, ctx, tabId, userId, sessionKey) {
  await ctx.ensureBrowser();
  let session = ctx.sessions.get(ctx.normalizeUserId(userId));
  const found = session && ctx.findTab(session, tabId);
  if (found) {
    return { session, found, tabState: found.tabState };
  }

  session = await ctx.getSession(userId);
  let sessionTabs = 0;
  for (const group of session.tabGroups.values()) sessionTabs += group.size;
  if (
    ctx.getTotalTabCount() >= ctx.maxTabsGlobal ||
    sessionTabs >= ctx.maxTabsPerSession
  ) {
    const recycled = await ctx.recycleOldestTab(session, req.reqId, userId);
    if (!recycled) {
      throw new Error('Maximum tabs per session reached');
    }
  }

  const page = await session.context.newPage();
  const tabState = ctx.createTabState(page);
  ctx.attachDownloadListener(tabState, tabId, ctx.log, ctx.pluginEvents, userId);
  const group = ctx.getTabGroup(session, sessionKey);
  group.set(tabId, tabState);
  ctx.refreshActiveTabsGauge();
  ctx.log('info', 'tab auto-created on navigate', {
    reqId: req.reqId,
    tabId,
    userId,
  });
  return { session, found: null, tabState };
}

function navigationTarget(url, macro, query, ctx) {
  let targetUrl = url;
  if (macro && macro !== '__NO__' && macro !== 'none' && macro !== 'null') {
    targetUrl = ctx.expandMacro(macro, query) || url;
  }
  if (!targetUrl) throw new Error('url or macro required');
  const urlErr = ctx.validateUrl(targetUrl);
  if (urlErr) throw new Error(urlErr);
  return targetUrl;
}

function navigationBadRequest(err) {
  return (
    err.message &&
    (err.message.startsWith('Blocked URL scheme') ||
      err.message === 'url or macro required')
  );
}

async function navigateCurrentPage(tabState, targetUrl, ctx) {
  tabState.lastRequestedUrl = targetUrl;
  const abortController = (tabState.navigateAbort = new AbortController());
  const gotoP = ctx.withPageLoadDuration('navigate', () =>
    tabState.page.goto(targetUrl, {
      waitUntil: 'domcontentloaded',
      timeout: 30000,
    }),
  );
  try {
    await Promise.race([
      gotoP,
      new Promise((_, reject) =>
        abortController.signal.addEventListener(
          'abort',
          () => reject(new Error('Navigation aborted: tab deleted')),
          { once: true },
        ),
      ),
    ]);
    tabState.visitedUrls.add(targetUrl);
    tabState.lastSnapshot = null;
  } catch (err) {
    gotoP.catch(() => {});
    throw err;
  } finally {
    tabState.navigateAbort = null;
  }
}

async function prewarmGoogleHome(tabState, isGoogleSearch, ctx) {
  if (!isGoogleSearch || tabState.visitedUrls.has('https://www.google.com/')) {
    return;
  }
  await ctx.withPageLoadDuration('navigate', () =>
    tabState.page.goto('https://www.google.com/', {
      waitUntil: 'domcontentloaded',
      timeout: 30000,
    }),
  );
  tabState.visitedUrls.add('https://www.google.com/');
  await tabState.page.waitForTimeout(1200);
}

async function recreateTabOnFreshContext(state) {
  const { ctx, currentSessionKey, tabId, tabState, userId } = state;
  const previousRetryCount = tabState.googleRetryCount || 0;
  ctx.browserRestartsTotal.labels('google_search_block').inc();
  const key = ctx.normalizeUserId(userId);
  const oldSession = ctx.sessions.get(key);
  if (oldSession) {
    await ctx.closeSession(key, oldSession, {
      reason: 'google_blocked_context_rotate',
      clearDownloads: true,
      clearLocks: true,
    });
  }
  const session = await ctx.getSession(userId);
  const group = ctx.getTabGroup(session, currentSessionKey);
  const page = await session.context.newPage();
  const nextTabState = ctx.createTabState(page);
  nextTabState.googleRetryCount = previousRetryCount + 1;
  ctx.attachDownloadListener(
    nextTabState,
    tabId,
    ctx.log,
    ctx.pluginEvents,
    userId,
  );
  group.set(tabId, nextTabState);
  ctx.refreshActiveTabsGauge();
  return { session, tabState: nextTabState };
}

async function navigateWithGoogleRecovery(req, ctx, state) {
  let { session, tabState } = state;
  const { currentSessionKey, isGoogleSearch, tabId, targetUrl, userId } = state;

  if (isGoogleSearch && ctx.proxyPool?.canRotateSessions) {
    await prewarmGoogleHome(tabState, isGoogleSearch, ctx);
  }
  await navigateCurrentPage(tabState, targetUrl, ctx);

  if (
    isGoogleSearch &&
    ctx.proxyPool?.canRotateSessions &&
    (await ctx.isGoogleSearchBlocked(tabState.page))
  ) {
    ctx.log('warn', 'google search blocked, rotating browser proxy session', {
      reqId: req.reqId,
      tabId,
      url: tabState.page.url(),
      proxySession: ctx.getBrowserLaunchProxy()?.sessionId || null,
    });
    ({ session, tabState } = await recreateTabOnFreshContext({
      ctx,
      currentSessionKey,
      tabId,
      tabState,
      userId,
    }));
    await prewarmGoogleHome(tabState, isGoogleSearch, ctx);
    await navigateCurrentPage(tabState, targetUrl, ctx);
  }

  return { session, tabState };
}

async function buildNavigationResult(tabId, tabState, isGoogleSearch, ctx) {
  if (ctx.isGoogleSerp(tabState.page.url())) {
    tabState.refs = new Map();
    return {
      ok: true,
      tabId,
      url: tabState.page.url(),
      refsAvailable: false,
      googleSerp: true,
    };
  }
  if (isGoogleSearch && (await ctx.isGoogleSearchBlocked(tabState.page))) {
    return {
      ok: false,
      tabId,
      url: tabState.page.url(),
      refsAvailable: false,
      googleBlocked: true,
    };
  }
  tabState.refs = await ctx.buildRefs(tabState.page);
  return {
    ok: true,
    tabId,
    url: tabState.page.url(),
    refsAvailable: tabState.refs.size > 0,
  };
}

/**
 * @openapi
 * /tabs/{tabId}/navigate:
 *   post:
 *     tags: [Navigation]
 *     summary: Navigate a tab to a URL or macro
 *     description: Navigate to a URL or expand a search macro. Auto-creates tab if not found.
 *     parameters:
 *       - name: tabId
 *         in: path
 *         required: true
 *         schema:
 *           type: string
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required: [userId]
 *             properties:
 *               userId:
 *                 type: string
 *               url:
 *                 type: string
 *               macro:
 *                 type: string
 *                 description: Search macro (e.g. @google_search).
 *               query:
 *                 type: string
 *                 description: Search query for macro.
 *               sessionKey:
 *                 type: string
 *               listItemId:
 *                 type: string
 *     responses:
 *       200:
 *         description: Navigation result with snapshot.
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *       400:
 *         description: Bad request.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 *       404:
 *         description: Tab not found.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
export function mountTabNavigationRoutes(app, ctx) {
  app.post('/tabs/:tabId/navigate', async (req, res) => {
    const tabId = req.params.tabId;

    try {
      const { userId, url, macro, query, sessionKey, listItemId } = req.body;
      if (!userId) return res.status(400).json({ error: 'userId required' });

      const result = await ctx.withUserLimit(userId, () =>
        ctx.withTimeout(
          (async () => {
            const resolvedSessionKey = sessionKey || listItemId || 'default';
            const initial = await ensureTabForNavigation(
              req,
              ctx,
              tabId,
              userId,
              resolvedSessionKey,
            );
            const targetUrl = navigationTarget(url, macro, query, ctx);
            initial.tabState.toolCalls++;
            initial.tabState.consecutiveTimeouts = 0;
            initial.tabState.consecutiveFailures = 0;

            return await ctx.withTabLock(
              tabId,
              async () => {
                const currentSessionKey =
                  initial.found?.listItemId || resolvedSessionKey;
                const isGoogleSearch = ctx.isGoogleSearchUrl(targetUrl);
                const navigated = await navigateWithGoogleRecovery(req, ctx, {
                  ...initial,
                  currentSessionKey,
                  isGoogleSearch,
                  tabId,
                  targetUrl,
                  userId,
                });
                return await buildNavigationResult(
                  tabId,
                  navigated.tabState,
                  isGoogleSearch,
                  ctx,
                );
              },
              ctx.requestTimeoutMs(),
            );
          })(),
          ctx.requestTimeoutMs(),
          'navigate',
        ),
      );

      ctx.log('info', 'navigated', { reqId: req.reqId, tabId, url: result.url });
      ctx.pluginEvents.emit('tab:navigated', {
        userId: req.body.userId,
        tabId,
        url: result.url,
        prevUrl: null,
      });
      res.json(result);
    } catch (err) {
      ctx.log('error', 'navigate failed', {
        reqId: req.reqId,
        tabId,
        error: err.message,
      });
      if (navigationBadRequest(err)) {
        return res.status(400).json({ error: ctx.safeError(err) });
      }
      ctx.handleRouteError(err, req, res);
    }
  });
}
