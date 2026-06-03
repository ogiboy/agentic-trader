function tabCount(session) {
  let total = 0;
  for (const group of session.tabGroups.values()) total += group.size;
  return total;
}

/**
 * @openapi
 * /:
 *   get:
 *     tags: [System]
 *     summary: Server status
 *     description: Returns basic server liveness and browser state.
 *     responses:
 *       200:
 *         description: Server status.
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 ok:
 *                   type: boolean
 *                 enabled:
 *                   type: boolean
 *                 running:
 *                   type: boolean
 *                 engine:
 *                   type: string
 *                 browserConnected:
 *                   type: boolean
 *                 browserRunning:
 *                   type: boolean
 */
function mountStatusRoute(app, ctx) {
  app.get('/', (req, res) => {
    const browser = ctx.getBrowser();
    const running = browser !== null && (browser.isConnected?.() ?? false);
    res.json({
      ok: true,
      enabled: true,
      running,
      engine: 'camoufox',
      browserConnected: running,
      browserRunning: running,
    });
  });
}

/**
 * @openapi
 * /tabs:
 *   get:
 *     tags: [Tabs]
 *     summary: List open tabs
 *     description: Returns all tabs for a given userId.
 *     parameters:
 *       - name: userId
 *         in: query
 *         schema:
 *           type: string
 *         description: Filter by session owner.
 *     responses:
 *       200:
 *         description: Tab list.
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 running:
 *                   type: boolean
 *                 tabs:
 *                   type: array
 *                   items:
 *                     type: object
 *                     properties:
 *                       tabId:
 *                         type: string
 *                       targetId:
 *                         type: string
 *                       url:
 *                         type: string
 *                       title:
 *                         type: string
 *                       listItemId:
 *                         type: string
 */
function mountListTabsRoute(app, ctx) {
  app.get('/tabs', async (req, res) => {
    try {
      const userId = req.query.userId;
      const session = ctx.sessions.get(ctx.normalizeUserId(userId));

      if (!session) return res.json({ running: true, tabs: [] });

      const tabs = [];
      for (const [listItemId, group] of session.tabGroups) {
        for (const [tabId, tabState] of group) {
          tabs.push({
            targetId: tabId,
            tabId,
            url: tabState.page.url(),
            title: await tabState.page.title().catch(() => ''),
            listItemId,
          });
        }
      }

      res.json({ running: true, tabs });
    } catch (err) {
      ctx.log('error', 'list tabs failed', {
        reqId: req.reqId,
        error: err.message,
      });
      ctx.handleRouteError(err, req, res);
    }
  });
}

/**
 * @openapi
 * /tabs/open:
 *   post:
 *     tags: [Legacy]
 *     summary: Open tab (OpenClaw format)
 *     deprecated: true
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required: [userId, url]
 *             properties:
 *               userId:
 *                 type: string
 *               url:
 *                 type: string
 *               listItemId:
 *                 type: string
 *     responses:
 *       200:
 *         description: Tab opened.
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
 */
function mountOpenTabRoute(app, ctx) {
  app.post('/tabs/open', async (req, res) => {
    try {
      const { url, userId, listItemId = 'default' } = req.body;
      if (!userId) return res.status(400).json({ error: 'userId is required' });
      if (!url) return res.status(400).json({ error: 'url is required' });

      const urlErr = ctx.validateUrl(url);
      if (urlErr) return res.status(400).json({ error: urlErr });

      const session = await ctx.getSession(userId);
      if (
        tabCount(session) >= ctx.maxTabsPerSession ||
        ctx.getTotalTabCount() >= ctx.maxTabsGlobal
      ) {
        const recycled = await ctx.recycleOldestTab(session, req.reqId, userId);
        if (!recycled) {
          return res
            .status(429)
            .json({ error: 'Maximum tabs per session reached' });
        }
      }

      const group = ctx.getTabGroup(session, listItemId);
      const page = await session.context.newPage();
      const tabId = ctx.fly.makeTabId();
      const tabState = ctx.createTabState(page);
      ctx.attachDownloadListener(
        tabState,
        tabId,
        ctx.log,
        ctx.pluginEvents,
        userId,
      );
      group.set(tabId, tabState);
      ctx.refreshActiveTabsGauge();

      await ctx.withPageLoadDuration('open_url', () =>
        page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 }),
      );
      tabState.visitedUrls.add(url);

      ctx.log('info', 'openclaw tab opened', {
        reqId: req.reqId,
        tabId,
        url: page.url(),
      });
      res.json({
        ok: true,
        targetId: tabId,
        tabId,
        url: page.url(),
        title: await page.title().catch(() => ''),
      });
    } catch (err) {
      ctx.log('error', 'openclaw tab open failed', {
        reqId: req.reqId,
        error: err.message,
      });
      ctx.handleRouteError(err, req, res);
    }
  });
}

/**
 * @openapi
 * /start:
 *   post:
 *     tags: [Browser]
 *     summary: Start browser
 *     description: Ensures the browser process is running. Idempotent.
 *     responses:
 *       200:
 *         description: Browser started.
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 ok:
 *                   type: boolean
 *                 profile:
 *                   type: string
 *       500:
 *         description: Launch failed.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
function mountStartRoute(app, ctx) {
  app.post('/start', async (req, res) => {
    try {
      await ctx.ensureBrowser();
      res.json({ ok: true, profile: 'camoufox' });
    } catch (err) {
      ctx.failuresTotal.labels('browser_launch', 'start').inc();
      res.status(500).json({ ok: false, error: ctx.safeError(err) });
    }
  });
}

/**
 * @openapi
 * /stop:
 *   post:
 *     tags: [Browser]
 *     summary: Stop browser
 *     description: Stops the browser and closes all sessions. Requires x-admin-key header.
 *     security:
 *       - BearerAuth: []
 *     responses:
 *       200:
 *         description: Browser stopped.
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 ok:
 *                   type: boolean
 *                 stopped:
 *                   type: boolean
 *                 profile:
 *                   type: string
 *       403:
 *         description: Forbidden.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
function mountStopRoute(app, ctx) {
  app.post('/stop', async (req, res) => {
    try {
      const adminKey = req.headers['x-admin-key'];
      if (!adminKey || !ctx.timingSafeCompare(adminKey, ctx.config.adminKey)) {
        return res.status(403).json({ error: 'Forbidden' });
      }
      await ctx.closeAllSessions('admin_stop', {
        clearDownloads: true,
        clearLocks: true,
      });
      await ctx.closeBrowserFully('admin_stop');
      res.json({ ok: true, stopped: true, profile: 'camoufox' });
    } catch (err) {
      res.status(500).json({ ok: false, error: ctx.safeError(err) });
    }
  });
}

/**
 * @openapi
 * /navigate:
 *   post:
 *     tags: [Legacy]
 *     summary: Navigate (OpenClaw format)
 *     description: Navigate with targetId in body instead of path param.
 *     deprecated: true
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required: [userId, url]
 *             properties:
 *               userId:
 *                 type: string
 *               targetId:
 *                 type: string
 *               url:
 *                 type: string
 *     responses:
 *       200:
 *         description: Navigation result.
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
function mountNavigateRoute(app, ctx) {
  app.post('/navigate', async (req, res) => {
    try {
      const { targetId, url, userId } = req.body;
      if (!userId) return res.status(400).json({ error: 'userId is required' });
      if (!url) return res.status(400).json({ error: 'url is required' });

      const urlErr = ctx.validateUrl(url);
      if (urlErr) return res.status(400).json({ error: urlErr });

      const session = ctx.sessions.get(ctx.normalizeUserId(userId));
      const found = session && ctx.findTab(session, targetId);
      if (!found) return res.status(404).json({ error: 'Tab not found' });

      const { tabState } = found;
      tabState.toolCalls++;
      tabState.consecutiveTimeouts = 0;
      tabState.consecutiveFailures = 0;

      const result = await ctx.withTabLock(targetId, async () => {
        await ctx.withPageLoadDuration('navigate', () =>
          tabState.page.goto(url, {
            waitUntil: 'domcontentloaded',
            timeout: 30000,
          }),
        );
        tabState.visitedUrls.add(url);
        tabState.lastSnapshot = null;

        if (ctx.isGoogleSerp(tabState.page.url())) {
          tabState.refs = new Map();
          return {
            ok: true,
            targetId,
            url: tabState.page.url(),
            googleSerp: true,
          };
        }

        tabState.refs = await ctx.buildRefs(tabState.page);
        return { ok: true, targetId, url: tabState.page.url() };
      });

      res.json(result);
    } catch (err) {
      ctx.log('error', 'openclaw navigate failed', {
        reqId: req.reqId,
        error: err.message,
      });
      ctx.handleRouteError(err, req, res);
    }
  });
}

export function mountLegacyCoreRoutes(app, ctx) {
  mountStatusRoute(app, ctx);
  mountListTabsRoute(app, ctx);
  mountOpenTabRoute(app, ctx);
  mountStartRoute(app, ctx);
  mountStopRoute(app, ctx);
  mountNavigateRoute(app, ctx);
}
