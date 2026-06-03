function findClickTab(ctx, userId, tabId) {
  const session = ctx.sessions.get(ctx.normalizeUserId(userId));
  const found = session && ctx.findTab(session, tabId);
  if (!found) return null;

  const { tabState } = found;
  tabState.toolCalls++;
  tabState.consecutiveTimeouts = 0;
  tabState.consecutiveFailures = 0;
  return tabState;
}

function remainingBudget(ctx, clickStart) {
  return Math.max(
    0,
    ctx.handlerTimeoutMs - 2000 - (Date.now() - clickStart),
  );
}

async function dispatchMouseSequence(ctx, tabState, locator) {
  const box = await locator.boundingBox();
  if (!box) throw new Error('Element not visible (no bounding box)');

  const x = box.x + box.width / 2;
  const y = box.y + box.height / 2;

  await tabState.page.mouse.move(x, y);
  await tabState.page.waitForTimeout(50);
  await tabState.page.mouse.down();
  await tabState.page.waitForTimeout(50);
  await tabState.page.mouse.up();

  ctx.log('info', 'mouse sequence dispatched', {
    x: x.toFixed(0),
    y: y.toFixed(0),
  });
}

async function clickLocator(ctx, tabState, locator, onGoogleSerp) {
  if (onGoogleSerp) {
    try {
      await locator.click({ timeout: 3000, force: true });
    } catch {
      ctx.log('warn', 'google force click failed, trying mouse sequence');
      await dispatchMouseSequence(ctx, tabState, locator);
    }
    return;
  }

  try {
    await locator.click({ timeout: 3000 });
  } catch (err) {
    if (err.message.includes('intercepts pointer events')) {
      ctx.log('warn', 'click intercepted, retrying with force');
      try {
        await locator.click({ timeout: 3000, force: true });
      } catch {
        ctx.log('warn', 'force click failed, trying mouse sequence');
        await dispatchMouseSequence(ctx, tabState, locator);
      }
    } else if (
      err.message.includes('not visible') ||
      err.message.toLowerCase().includes('timeout')
    ) {
      ctx.log('warn', 'click timeout, trying mouse sequence');
      await dispatchMouseSequence(ctx, tabState, locator);
    } else {
      throw err;
    }
  }
}

async function locatorForClick(ctx, tabState, ref, clickStart) {
  let locator = ctx.refToLocator(tabState.page, ref, tabState.refs);
  if (!locator) {
    ctx.log('info', 'auto-refreshing refs before click', {
      ref,
      hadRefs: tabState.refs.size,
    });
    try {
      const preClickBudget = Math.min(4000, remainingBudget(ctx, clickStart));
      tabState.refs = await ctx.refreshTabRefs(tabState, {
        reason: 'pre_click',
        timeoutMs: preClickBudget,
      });
    } catch (err) {
      if (
        err.message === 'pre_click_refs_timeout' ||
        err.message === 'buildRefs_timeout'
      ) {
        ctx.log(
          'warn',
          'pre-click buildRefs timed out, proceeding without refresh',
        );
      } else {
        throw err;
      }
    }
    locator = ctx.refToLocator(tabState.page, ref, tabState.refs);
  }
  if (!locator) {
    const maxRef = tabState.refs.size > 0 ? `e${tabState.refs.size}` : 'none';
    throw new ctx.StaleRefsError(ref, maxRef, tabState.refs.size);
  }
  return locator;
}

async function finishClick(ctx, tabState, onGoogleSerp, clickStart) {
  if (onGoogleSerp) {
    try {
      await tabState.page.waitForLoadState('domcontentloaded', {
        timeout: 3000,
      });
    } catch {}
    await tabState.page.waitForTimeout(200);
    tabState.lastSnapshot = null;
    tabState.refs = new Map();
    const newUrl = tabState.page.url();
    tabState.visitedUrls.add(newUrl);
    return { ok: true, url: newUrl, refsAvailable: false };
  }

  await tabState.page.waitForTimeout(500);
  tabState.lastSnapshot = null;
  const postClickBudget = Math.max(2000, remainingBudget(ctx, clickStart));
  try {
    tabState.refs = await ctx.refreshTabRefs(tabState, {
      reason: 'post_click',
      timeoutMs: postClickBudget,
    });
  } catch (err) {
    if (
      err.message === 'post_click_refs_timeout' ||
      err.message === 'buildRefs_timeout'
    ) {
      ctx.log('warn', 'post-click buildRefs timed out, returning without refs', {
        budget: postClickBudget,
        elapsed: Date.now() - clickStart,
      });
      tabState.refs = new Map();
    } else {
      throw err;
    }
  }

  const newUrl = tabState.page.url();
  tabState.visitedUrls.add(newUrl);
  return { ok: true, url: newUrl, refsAvailable: tabState.refs.size > 0 };
}

async function executeClick(ctx, tabState, input) {
  const clickStart = Date.now();
  const onGoogleSerp = ctx.isGoogleSerp(tabState.page.url());
  if (input.ref) {
    const locator = await locatorForClick(ctx, tabState, input.ref, clickStart);
    await clickLocator(ctx, tabState, locator, onGoogleSerp);
  } else {
    const locator = tabState.page.locator(input.selector);
    await clickLocator(ctx, tabState, locator, onGoogleSerp);
  }
  return finishClick(ctx, tabState, onGoogleSerp, clickStart);
}

async function refreshAfterClickTimeout(ctx, req, res, err, tabId) {
  const session = ctx.sessions.get(ctx.normalizeUserId(req.body.userId));
  const found = session && ctx.findTab(session, tabId);
  if (found?.tabState?.page && !found.tabState.page.isClosed()) {
    found.tabState.refs = await ctx.refreshTabRefs(found.tabState, {
      reason: 'click_timeout',
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
 * /tabs/{tabId}/click:
 *   post:
 *     tags: [Interaction]
 *     summary: Click an element
 *     description: Click by element ref, CSS selector, or coordinates.
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
 *               ref:
 *                 type: string
 *                 description: Element ref ID (e.g. "e3").
 *               selector:
 *                 type: string
 *                 description: CSS selector fallback.
 *               doubleClick:
 *                 type: boolean
 *               coordinates:
 *                 type: object
 *                 properties:
 *                   x:
 *                     type: number
 *                   y:
 *                     type: number
 *     responses:
 *       200:
 *         description: Click result with optional post-action snapshot.
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
export function mountTabClickRoutes(app, ctx) {
  app.post('/tabs/:tabId/click', async (req, res) => {
    const tabId = req.params.tabId;

    try {
      const { userId, ref, selector } = req.body;
      if (!userId) return res.status(400).json({ error: 'userId required' });
      const tabState = findClickTab(ctx, userId, tabId);
      if (!tabState) return res.status(404).json({ error: 'Tab not found' });

      if (!ref && !selector) {
        return res.status(400).json({ error: 'ref or selector required' });
      }

      const result = await ctx.withUserLimit(userId, () =>
        ctx.withTabLock(tabId, () =>
          executeClick(ctx, tabState, { ref, selector }),
        ),
      );

      ctx.log('info', 'clicked', { reqId: req.reqId, tabId, url: result.url });
      ctx.pluginEvents.emit('tab:click', {
        userId: req.body.userId,
        tabId,
        ref: req.body.ref,
        selector: req.body.selector,
      });
      res.json(result);
    } catch (err) {
      ctx.log('error', 'click failed', {
        reqId: req.reqId,
        tabId,
        error: err.message,
      });
      if (err.message?.includes('timed out')) {
        try {
          const response = await refreshAfterClickTimeout(
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
