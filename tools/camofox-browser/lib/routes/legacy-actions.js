async function refLocator(ctx, tabState, ref, reason) {
  let locator = ctx.refToLocator(tabState.page, ref, tabState.refs);
  if (!locator) {
    ctx.log('info', `auto-refreshing refs before ${reason} (openclaw)`, {
      ref,
      hadRefs: tabState.refs.size,
    });
    tabState.refs = await ctx.buildRefs(tabState.page);
    locator = ctx.refToLocator(tabState.page, ref, tabState.refs);
  }
  if (!locator) {
    const maxRef = tabState.refs.size > 0 ? `e${tabState.refs.size}` : 'none';
    throw new ctx.StaleRefsError(ref, maxRef, tabState.refs.size);
  }
  return locator;
}

async function runClick(ctx, tabState, targetId, params) {
  const { ref, selector, doubleClick } = params;
  if (!ref && !selector) throw new Error('ref or selector required');

  const clickElement = async (locatorOrSelector, isLocator) => {
    const locator = isLocator
      ? locatorOrSelector
      : tabState.page.locator(locatorOrSelector);
    const clickOpts = { timeout: 3000 };
    if (doubleClick) clickOpts.clickCount = 2;

    try {
      await locator.click(clickOpts);
    } catch (err) {
      if (err.message.includes('intercepts pointer events')) {
        await locator.click({ ...clickOpts, force: true });
      } else {
        throw err;
      }
    }
  };

  if (ref) {
    await clickElement(await refLocator(ctx, tabState, ref, 'click'), true);
  } else {
    await clickElement(selector, false);
  }

  await tabState.page.waitForTimeout(500);
  tabState.refs = await ctx.buildRefs(tabState.page);
  return { ok: true, targetId, url: tabState.page.url() };
}

async function runType(ctx, tabState, targetId, params) {
  const { ref, selector, text, submit, mode = 'fill', delay = 30 } = params;
  if (mode === 'fill' && !ref && !selector) {
    throw new Error('ref or selector required for mode=fill');
  }
  if (typeof text !== 'string') throw new Error('text is required');
  if (mode !== 'fill' && mode !== 'keyboard') {
    throw new Error("mode must be 'fill' or 'keyboard'");
  }

  const locator = ref ? await refLocator(ctx, tabState, ref, 'type') : null;
  if (mode === 'fill') {
    if (locator) {
      await locator.fill(text, { timeout: 10000 });
    } else {
      await tabState.page.fill(selector, text, { timeout: 10000 });
    }
  } else {
    if (locator) {
      await locator.focus({ timeout: 10000 });
    } else if (selector) {
      await tabState.page.focus(selector, { timeout: 10000 });
    }
    await tabState.page.keyboard.type(text, { delay });
  }
  if (submit) await tabState.page.keyboard.press('Enter');
  return { ok: true, targetId };
}

async function runScroll(ctx, tabState, targetId, params) {
  const { ref, direction = 'down', amount = 500 } = params;
  if (ref) {
    const locator = await refLocator(ctx, tabState, ref, 'scroll');
    await locator.scrollIntoViewIfNeeded({ timeout: 5000 });
  } else {
    const isVertical = direction === 'up' || direction === 'down';
    const delta = direction === 'up' || direction === 'left' ? -amount : amount;
    await tabState.page.mouse.wheel(
      isVertical ? 0 : delta,
      isVertical ? delta : 0,
    );
  }
  await tabState.page.waitForTimeout(300);
  return { ok: true, targetId };
}

async function runHover(ctx, tabState, targetId, params) {
  const { ref, selector } = params;
  if (!ref && !selector) throw new Error('ref or selector required');

  if (ref) {
    const locator = await refLocator(ctx, tabState, ref, 'hover');
    await locator.hover({ timeout: 5000 });
  } else {
    await tabState.page.locator(selector).hover({ timeout: 5000 });
  }
  return { ok: true, targetId };
}

async function runWait(tabState, targetId, params) {
  const { timeMs, text, loadState } = params;
  if (timeMs) {
    await tabState.page.waitForTimeout(timeMs);
  } else if (text) {
    await tabState.page.waitForSelector(`text=${text}`, { timeout: 30000 });
  } else if (loadState) {
    await tabState.page.waitForLoadState(loadState, { timeout: 30000 });
  }
  return { ok: true, targetId, url: tabState.page.url() };
}

async function runLegacyAction(ctx, found, kind, targetId, params) {
  const { tabState } = found;
  switch (kind) {
    case 'click':
      return runClick(ctx, tabState, targetId, params);
    case 'type':
      return runType(ctx, tabState, targetId, params);
    case 'press': {
      const { key } = params;
      if (!key) throw new Error('key is required');
      await tabState.page.keyboard.press(key);
      return { ok: true, targetId };
    }
    case 'scroll':
    case 'scrollIntoView':
      return runScroll(ctx, tabState, targetId, params);
    case 'hover':
      return runHover(ctx, tabState, targetId, params);
    case 'wait':
      return runWait(tabState, targetId, params);
    case 'close': {
      await ctx.safePageClose(tabState.page);
      found.group.delete(targetId);
      const lock = ctx.tabLocks.get(targetId);
      if (lock) lock.drain();
      ctx.tabLocks.delete(targetId);
      return { ok: true, targetId };
    }
    default:
      throw new Error(`Unsupported action kind: ${kind}`);
  }
}

/**
 * @openapi
 * /act:
 *   post:
 *     tags: [Legacy]
 *     summary: Combined action (OpenClaw format)
 *     description: Routes to click/type/scroll/press/etc based on "kind" parameter.
 *     deprecated: true
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required: [userId, kind]
 *             properties:
 *               userId:
 *                 type: string
 *               kind:
 *                 type: string
 *                 description: 'Action kind: click, type, scroll, press, key, select_option, drag, hover, screenshot, wait, back, forward.'
 *               targetId:
 *                 type: string
 *               ref:
 *                 type: string
 *               selector:
 *                 type: string
 *               text:
 *                 type: string
 *               key:
 *                 type: string
 *               direction:
 *                 type: string
 *               url:
 *                 type: string
 *     responses:
 *       200:
 *         description: Action result.
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
export function mountLegacyActionRoutes(app, ctx) {
  app.post('/act', async (req, res) => {
    try {
      const { kind, targetId, userId, ...params } = req.body;
      if (!userId) return res.status(400).json({ error: 'userId is required' });
      if (!kind) return res.status(400).json({ error: 'kind is required' });

      const session = ctx.sessions.get(ctx.normalizeUserId(userId));
      const found = session && ctx.findTab(session, targetId);
      if (!found) return res.status(404).json({ error: 'Tab not found' });

      const { tabState } = found;
      tabState.toolCalls++;
      tabState.consecutiveTimeouts = 0;
      tabState.consecutiveFailures = 0;

      const result = await ctx.withTabLock(targetId, () =>
        runLegacyAction(ctx, found, kind, targetId, params),
      );
      res.json(result);
    } catch (err) {
      ctx.log('error', 'act failed', {
        reqId: req.reqId,
        kind: req.body?.kind,
        error: err.message,
      });
      ctx.handleRouteError(err, req, res);
    }
    return undefined;
  });
}
