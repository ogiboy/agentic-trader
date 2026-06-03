function tabStateForRequest(req, ctx) {
  const { userId } = req.body;
  const session = ctx.sessions.get(ctx.normalizeUserId(userId));
  const found = session && ctx.findTab(session, req.params.tabId);
  if (!found) return null;

  const { tabState } = found;
  tabState.toolCalls++;
  tabState.consecutiveTimeouts = 0;
  tabState.consecutiveFailures = 0;
  return tabState;
}

async function refreshRefsResult(tabState, ctx) {
  tabState.refs = await ctx.buildRefs(tabState.page);
  return { ok: true, url: tabState.page.url() };
}

/**
 * @openapi
 * /tabs/{tabId}/back:
 *   post:
 *     tags: [Navigation]
 *     summary: Go back
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
 *     responses:
 *       200:
 *         description: Navigated back.
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 ok:
 *                   type: boolean
 *                 url:
 *                   type: string
 *       404:
 *         description: Tab not found.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
function mountBackRoute(app, ctx) {
  app.post('/tabs/:tabId/back', async (req, res) => {
    const tabId = req.params.tabId;

    try {
      const tabState = tabStateForRequest(req, ctx);
      if (!tabState) return res.status(404).json({ error: 'Tab not found' });

      const result = await ctx.withTabLock(tabId, async () => {
        try {
          await tabState.page.goBack({ timeout: 10000 });
        } catch (navErr) {
          if (
            navErr.message &&
            navErr.message.includes('NS_BINDING_CANCELLED')
          ) {
            ctx.log('info', 'goBack cancelled old load (expected)', {
              reqId: req.reqId,
              tabId,
            });
          } else {
            throw navErr;
          }
        }
        return refreshRefsResult(tabState, ctx);
      });

      res.json(result);
    } catch (err) {
      ctx.log('error', 'back failed', {
        reqId: req.reqId,
        error: err.message,
      });
      ctx.handleRouteError(err, req, res);
    }
  });
}

/**
 * @openapi
 * /tabs/{tabId}/forward:
 *   post:
 *     tags: [Navigation]
 *     summary: Go forward
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
 *     responses:
 *       200:
 *         description: Navigated forward.
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 ok:
 *                   type: boolean
 *                 url:
 *                   type: string
 *       404:
 *         description: Tab not found.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
function mountForwardRoute(app, ctx) {
  app.post('/tabs/:tabId/forward', async (req, res) => {
    const tabId = req.params.tabId;

    try {
      const tabState = tabStateForRequest(req, ctx);
      if (!tabState) return res.status(404).json({ error: 'Tab not found' });

      const result = await ctx.withTabLock(tabId, async () => {
        await tabState.page.goForward({ timeout: 10000 });
        return refreshRefsResult(tabState, ctx);
      });

      res.json(result);
    } catch (err) {
      ctx.log('error', 'forward failed', {
        reqId: req.reqId,
        error: err.message,
      });
      ctx.handleRouteError(err, req, res);
    }
  });
}

/**
 * @openapi
 * /tabs/{tabId}/refresh:
 *   post:
 *     tags: [Navigation]
 *     summary: Refresh page
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
 *     responses:
 *       200:
 *         description: Page refreshed.
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 ok:
 *                   type: boolean
 *                 url:
 *                   type: string
 *       404:
 *         description: Tab not found.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
function mountRefreshRoute(app, ctx) {
  app.post('/tabs/:tabId/refresh', async (req, res) => {
    const tabId = req.params.tabId;

    try {
      const tabState = tabStateForRequest(req, ctx);
      if (!tabState) return res.status(404).json({ error: 'Tab not found' });

      const result = await ctx.withTabLock(tabId, async () => {
        await tabState.page.reload({ timeout: 30000 });
        return refreshRefsResult(tabState, ctx);
      });

      res.json(result);
    } catch (err) {
      ctx.log('error', 'refresh failed', {
        reqId: req.reqId,
        error: err.message,
      });
      ctx.handleRouteError(err, req, res);
    }
  });
}

export function mountTabHistoryRoutes(app, ctx) {
  mountBackRoute(app, ctx);
  mountForwardRoute(app, ctx);
  mountRefreshRoute(app, ctx);
}
