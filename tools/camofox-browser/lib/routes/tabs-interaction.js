function bodyTabState(req, ctx, userId, tabId) {
  const session = ctx.sessions.get(ctx.normalizeUserId(userId));
  const found = session && ctx.findTab(session, tabId);
  return found?.tabState || null;
}

function markToolCall(tabState) {
  tabState.toolCalls++;
  tabState.consecutiveTimeouts = 0;
  tabState.consecutiveFailures = 0;
}

/**
 * @openapi
 * /tabs/{tabId}/wait:
 *   post:
 *     tags: [Interaction]
 *     summary: Wait for a selector or timeout
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
 *               selector:
 *                 type: string
 *               timeout:
 *                 type: integer
 *                 description: Max wait in ms.
 *     responses:
 *       200:
 *         description: Wait completed.
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
function mountWaitRoute(app, ctx) {
  app.post('/tabs/:tabId/wait', async (req, res) => {
    try {
      const { userId, timeout = 10000, waitForNetwork = true } = req.body;
      const tabState = bodyTabState(req, ctx, userId, req.params.tabId);
      if (!tabState) return res.status(404).json({ error: 'Tab not found' });

      const ready = await ctx.waitForPageReady(tabState.page, {
        timeout,
        waitForNetwork,
      });

      res.json({ ok: true, ready });
    } catch (err) {
      ctx.log('error', 'wait failed', {
        reqId: req.reqId,
        error: err.message,
      });
      ctx.handleRouteError(err, req, res);
    }
  });
}

/**
 * @openapi
 * /tabs/{tabId}/press:
 *   post:
 *     tags: [Interaction]
 *     summary: Press a keyboard key
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
 *             required: [userId, key]
 *             properties:
 *               userId:
 *                 type: string
 *               key:
 *                 type: string
 *                 description: Key name (e.g. "Enter", "Escape", "Tab").
 *     responses:
 *       200:
 *         description: Key pressed.
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
function mountPressRoute(app, ctx) {
  app.post('/tabs/:tabId/press', async (req, res) => {
    const tabId = req.params.tabId;

    try {
      const { userId, key } = req.body;
      const tabState = bodyTabState(req, ctx, userId, tabId);
      if (!tabState) return res.status(404).json({ error: 'Tab not found' });

      markToolCall(tabState);
      await ctx.withTabLock(tabId, async () => {
        await tabState.page.keyboard.press(key);
      });

      ctx.pluginEvents.emit('tab:press', { userId, tabId, key });
      res.json({ ok: true });
    } catch (err) {
      ctx.log('error', 'press failed', {
        reqId: req.reqId,
        error: err.message,
      });
      ctx.handleRouteError(err, req, res);
    }
  });
}

/**
 * @openapi
 * /tabs/{tabId}/scroll:
 *   post:
 *     tags: [Interaction]
 *     summary: Scroll the page
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
 *               direction:
 *                 type: string
 *                 description: '"up" or "down" (default "down").'
 *               amount:
 *                 type: integer
 *                 description: Pixels to scroll.
 *     responses:
 *       200:
 *         description: Scroll result.
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
function mountScrollRoute(app, ctx) {
  app.post('/tabs/:tabId/scroll', async (req, res) => {
    try {
      const { userId, direction = 'down', amount = 500 } = req.body;
      const tabState = bodyTabState(req, ctx, userId, req.params.tabId);
      if (!tabState) return res.status(404).json({ error: 'Tab not found' });

      markToolCall(tabState);
      const isVertical = direction === 'up' || direction === 'down';
      const delta =
        direction === 'up' || direction === 'left' ? -amount : amount;
      await tabState.page.mouse.wheel(
        isVertical ? 0 : delta,
        isVertical ? delta : 0,
      );
      await tabState.page.waitForTimeout(300);

      ctx.pluginEvents.emit('tab:scroll', {
        userId,
        tabId: req.params.tabId,
        direction,
        amount,
      });
      res.json({ ok: true });
    } catch (err) {
      ctx.log('error', 'scroll failed', {
        reqId: req.reqId,
        error: err.message,
      });
      ctx.handleRouteError(err, req, res);
    }
  });
}

export function mountTabInteractionRoutes(app, ctx) {
  mountWaitRoute(app, ctx);
  mountPressRoute(app, ctx);
  mountScrollRoute(app, ctx);
}
