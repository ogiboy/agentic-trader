function userIdFromRequest(req) {
  return req.query.userId || req.body?.userId;
}

async function createTab(req, ctx, userId, sessionKey, url, trace) {
  const existing = ctx.sessions.get(ctx.normalizeUserId(userId));
  if (trace && existing && !existing.tracePath) {
    throw Object.assign(
      new Error(
        'trace must be set on session creation. DELETE /sessions/:userId first to restart with tracing.',
      ),
      { statusCode: 409 },
    );
  }
  const session = await ctx.getSession(userId, { trace: !!trace });
  let totalTabs = 0;
  for (const group of session.tabGroups.values()) totalTabs += group.size;

  if (
    totalTabs >= ctx.maxTabsPerSession ||
    ctx.getTotalTabCount() >= ctx.maxTabsGlobal
  ) {
    const recycled = await ctx.recycleOldestTab(session, req.reqId, userId);
    if (!recycled) {
      throw Object.assign(new Error('Maximum tabs per session reached'), {
        statusCode: 429,
      });
    }
  }

  const group = ctx.getTabGroup(session, sessionKey);
  const page = await session.context.newPage();
  const tabId = ctx.fly.makeTabId();
  const tabState = ctx.createTabState(page);
  ctx.attachDownloadListener(tabState, tabId, ctx.log, ctx.pluginEvents, userId);
  group.set(tabId, tabState);
  ctx.refreshActiveTabsGauge();

  if (url) {
    const urlErr = ctx.validateUrl(url);
    if (urlErr) throw Object.assign(new Error(urlErr), { statusCode: 400 });
    tabState.lastRequestedUrl = url;
    await ctx.withPageLoadDuration('open_url', () =>
      page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 }),
    );
    tabState.visitedUrls.add(url);
  }

  ctx.pluginEvents.emit('tab:created', {
    userId,
    tabId,
    page,
    url: page.url(),
  });
  ctx.log('info', 'tab created', {
    reqId: req.reqId,
    tabId,
    userId,
    sessionKey,
    url: page.url(),
  });
  return { tabId, url: page.url() };
}

/**
 * @openapi
 * /tabs:
 *   post:
 *     tags: [Tabs]
 *     summary: Create a new tab
 *     description: Creates a tab in the given session. Optionally navigates to an initial URL.
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required: [userId, sessionKey]
 *             properties:
 *               userId:
 *                 type: string
 *                 description: Session owner.
 *               sessionKey:
 *                 type: string
 *                 description: Tab group identifier.
 *               listItemId:
 *                 type: string
 *                 description: Legacy alias for sessionKey.
 *               url:
 *                 type: string
 *                 description: Optional initial URL.
 *               trace:
 *                 type: boolean
 *                 description: Enable Playwright tracing for this session (screenshots, DOM snapshots, network). Must be set on first tab creation; cannot be added to an existing session.
 *     responses:
 *       200:
 *         description: Tab created.
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 tabId:
 *                   type: string
 *                 url:
 *                   type: string
 *       400:
 *         description: Missing required fields.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 *       429:
 *         description: Tab limit reached.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 *       409:
 *         description: Cannot enable tracing on an existing session.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
function mountCreateTabRoute(app, ctx) {
  app.post('/tabs', async (req, res) => {
    try {
      const { userId, sessionKey, listItemId, url, trace } = req.body;
      const resolvedSessionKey = sessionKey || listItemId;
      if (!userId || !resolvedSessionKey) {
        return res
          .status(400)
          .json({ error: 'userId and sessionKey required' });
      }

      const result = await ctx.withTimeout(
        createTab(req, ctx, userId, resolvedSessionKey, url, trace),
        ctx.requestTimeoutMs(),
        'tab create',
      );
      res.json(result);
    } catch (err) {
      ctx.log('error', 'tab create failed', {
        reqId: req.reqId,
        error: err.message,
      });
      ctx.handleRouteError(err, req, res);
    }
  });
}

/**
 * @openapi
 * /tabs/{tabId}:
 *   delete:
 *     tags: [Tabs]
 *     summary: Close a tab
 *     parameters:
 *       - name: tabId
 *         in: path
 *         required: true
 *         schema:
 *           type: string
 *       - name: userId
 *         in: query
 *         required: true
 *         schema:
 *           type: string
 *     responses:
 *       200:
 *         description: Tab closed.
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 ok:
 *                   type: boolean
 *       404:
 *         description: Tab not found.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
function mountCloseTabRoute(app, ctx) {
  app.delete('/tabs/:tabId', async (req, res) => {
    try {
      const userId = userIdFromRequest(req);
      if (!userId) {
        return res
          .status(400)
          .json({ error: 'userId required (query or body)' });
      }
      const session = ctx.sessions.get(ctx.normalizeUserId(userId));
      const found = session && ctx.findTab(session, req.params.tabId);
      if (found) {
        if (found.tabState.navigateAbort) found.tabState.navigateAbort.abort();
        await ctx.clearTabDownloads(found.tabState);
        await ctx.safePageClose(found.tabState.page);
        found.group.delete(req.params.tabId);
        const lock = ctx.tabLocks.get(req.params.tabId);
        if (lock) lock.drain();
        ctx.tabLocks.delete(req.params.tabId);
        ctx.refreshTabLockQueueDepth();
        if (found.group.size === 0) {
          session.tabGroups.delete(found.listItemId);
        }
        ctx.refreshActiveTabsGauge();
        ctx.log('info', 'tab closed', {
          reqId: req.reqId,
          tabId: req.params.tabId,
          userId,
        });
      }
      res.json({ ok: true });
    } catch (err) {
      ctx.log('error', 'tab close failed', {
        reqId: req.reqId,
        error: err.message,
      });
      ctx.handleRouteError(err, req, res);
    }
  });
}

/**
 * @openapi
 * /tabs/group/{listItemId}:
 *   delete:
 *     tags: [Tabs]
 *     summary: Close all tabs in a group
 *     parameters:
 *       - name: listItemId
 *         in: path
 *         required: true
 *         schema:
 *           type: string
 *       - name: userId
 *         in: query
 *         required: true
 *         schema:
 *           type: string
 *     responses:
 *       200:
 *         description: Group closed.
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 ok:
 *                   type: boolean
 *                 closed:
 *                   type: integer
 *       404:
 *         description: Session not found.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
function mountCloseGroupRoute(app, ctx) {
  app.delete('/tabs/group/:listItemId', async (req, res) => {
    try {
      const userId = userIdFromRequest(req);
      if (!userId) {
        return res
          .status(400)
          .json({ error: 'userId required (query or body)' });
      }
      const session = ctx.sessions.get(ctx.normalizeUserId(userId));
      const group = session?.tabGroups.get(req.params.listItemId);
      if (group) {
        for (const [tabId, tabState] of group) {
          await ctx.clearTabDownloads(tabState);
          await ctx.safePageClose(tabState.page);
          const lock = ctx.tabLocks.get(tabId);
          if (lock) {
            lock.drain();
            ctx.tabLocks.delete(tabId);
          }
        }
        session.tabGroups.delete(req.params.listItemId);
        ctx.refreshTabLockQueueDepth();
        ctx.refreshActiveTabsGauge();
        ctx.log('info', 'tab group closed', {
          reqId: req.reqId,
          listItemId: req.params.listItemId,
          userId,
        });
      }
      res.json({ ok: true });
    } catch (err) {
      ctx.log('error', 'tab group close failed', {
        reqId: req.reqId,
        error: err.message,
      });
      ctx.handleRouteError(err, req, res);
    }
  });
}

export function mountTabLifecycleRoutes(app, ctx) {
  mountCreateTabRoute(app, ctx);
  mountCloseTabRoute(app, ctx);
  mountCloseGroupRoute(app, ctx);
}
