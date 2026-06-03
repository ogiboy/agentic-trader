function findTypingTab(ctx, userId, tabId) {
  const session = ctx.sessions.get(ctx.normalizeUserId(userId));
  const found = session && ctx.findTab(session, tabId);
  if (!found) return null;

  const { tabState } = found;
  tabState.toolCalls++;
  tabState.consecutiveTimeouts = 0;
  tabState.consecutiveFailures = 0;
  return tabState;
}

function validateTypingBody(req, res) {
  const { mode = 'fill', ref, selector, text } = req.body;
  if (mode !== 'fill' && mode !== 'keyboard') {
    res.status(400).json({ error: "mode must be 'fill' or 'keyboard'" });
    return false;
  }
  if (typeof text !== 'string') {
    res.status(400).json({ error: 'text is required' });
    return false;
  }
  if (mode === 'fill' && !ref && !selector) {
    res.status(400).json({ error: 'ref or selector required for mode=fill' });
    return false;
  }
  return true;
}

async function locatorForTyping(ctx, tabState, ref, mode) {
  if (!ref) return null;
  let locator = ctx.refToLocator(tabState.page, ref, tabState.refs);
  if (!locator) {
    ctx.log('info', 'auto-refreshing refs before type', {
      ref,
      hadRefs: tabState.refs.size,
      mode,
    });
    tabState.refs = await ctx.refreshTabRefs(tabState, { reason: 'type' });
    locator = ctx.refToLocator(tabState.page, ref, tabState.refs);
  }
  if (!locator) {
    const maxRef = tabState.refs.size > 0 ? `e${tabState.refs.size}` : 'none';
    throw new ctx.StaleRefsError(ref, maxRef, tabState.refs.size);
  }
  return locator;
}

async function typeIntoTarget(ctx, tabState, input, locator) {
  const { delay, mode, selector, text } = input;
  if (mode === 'fill') {
    if (locator) {
      await locator.fill(text, { timeout: 10000 });
    } else {
      await tabState.page.fill(selector, text, { timeout: 10000 });
    }
    return;
  }

  if (locator) {
    await locator.focus({ timeout: 10000 });
  } else if (selector) {
    await tabState.page.focus(selector, { timeout: 10000 });
  }
  await tabState.page.keyboard.type(text, { delay });
}

async function refreshAfterTypingError(ctx, req, res, err, tabId) {
  const session = ctx.sessions.get(ctx.normalizeUserId(req.body.userId));
  const found = session && ctx.findTab(session, tabId);
  if (found?.tabState?.page && !found.tabState.page.isClosed()) {
    found.tabState.refs = await ctx.refreshTabRefs(found.tabState, {
      reason: 'type_timeout',
    });
    found.tabState.lastSnapshot = null;
    return res.status(500).json({
      error: ctx.safeError(err),
      hint: 'The page may have changed. Call snapshot to see the current state and retry.',
      url: found.tabState.page.url(),
      refsCount: found.tabState.refs.size,
    });
  }
  return null;
}

/**
 * @openapi
 * /tabs/{tabId}/type:
 *   post:
 *     tags: [Interaction]
 *     summary: Type text into an element
 *     description: Types text into a focused element or a specific ref/selector.
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
 *             required: [userId, text]
 *             properties:
 *               userId:
 *                 type: string
 *               ref:
 *                 type: string
 *               selector:
 *                 type: string
 *               text:
 *                 type: string
 *               clear:
 *                 type: boolean
 *                 description: Clear field before typing.
 *               submit:
 *                 type: boolean
 *                 description: Press Enter after typing.
 *     responses:
 *       200:
 *         description: Type result.
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
export function mountTabTypingRoutes(app, ctx) {
  app.post('/tabs/:tabId/type', async (req, res) => {
    const tabId = req.params.tabId;

    try {
      const {
        userId,
        ref,
        selector,
        text,
        mode = 'fill',
        delay = 30,
        submit = false,
        pressEnter = false,
      } = req.body;
      const tabState = findTypingTab(ctx, userId, tabId);
      if (!tabState) return res.status(404).json({ error: 'Tab not found' });
      if (!validateTypingBody(req, res)) return undefined;

      const shouldSubmit = submit || pressEnter;
      await ctx.withTabLock(tabId, async () => {
        const locator = await locatorForTyping(ctx, tabState, ref, mode);
        await typeIntoTarget(
          ctx,
          tabState,
          { delay, mode, selector, text },
          locator,
        );
        if (shouldSubmit) await tabState.page.keyboard.press('Enter');
      });

      ctx.pluginEvents.emit('tab:type', {
        userId: req.body.userId,
        tabId,
        text: req.body.text,
        ref: req.body.ref,
        mode: req.body.mode || 'fill',
      });
      res.json({ ok: true });
    } catch (err) {
      ctx.log('error', 'type failed', {
        reqId: req.reqId,
        error: err.message,
      });
      if (
        err.message?.includes('timed out') ||
        err.message?.includes('not an <input>')
      ) {
        try {
          const response = await refreshAfterTypingError(
            ctx,
            req,
            res,
            err,
            tabId,
          );
          if (response) return response;
        } catch (refreshErr) {
          ctx.log('warn', 'post-timeout refresh failed', {
            error: refreshErr.message,
          });
        }
      }
      ctx.handleRouteError(err, req, res);
    }
    return undefined;
  });
}
