function buildWindowResponse(tabState, win, url) {
  return {
    url,
    snapshot: win.text,
    refsCount: tabState.refs.size,
    truncated: win.truncated,
    totalChars: win.totalChars,
    hasMore: win.hasMore,
    nextOffset: win.nextOffset,
  };
}

async function attachScreenshot(req, response, tabState) {
  if (req.query.includeScreenshot !== 'true') return response;
  const pngBuffer = await tabState.page.screenshot({ type: 'png' });
  response.screenshot = {
    data: pngBuffer.toString('base64'),
    mimeType: 'image/png',
  };
  return response;
}

function copyRotatedTabState(tabState, rotated) {
  tabState.page = rotated.tabState.page;
  tabState.refs = rotated.tabState.refs;
  tabState.visitedUrls = rotated.tabState.visitedUrls;
  tabState.downloads = rotated.tabState.downloads;
  tabState.toolCalls = rotated.tabState.toolCalls;
  tabState.consecutiveTimeouts = rotated.tabState.consecutiveTimeouts;
  tabState.lastSnapshot = rotated.tabState.lastSnapshot;
  tabState.lastRequestedUrl = rotated.tabState.lastRequestedUrl;
  tabState.googleRetryCount = rotated.tabState.googleRetryCount;
}

async function rotateBlockedGoogleTab(req, ctx, state) {
  const { found, tabState, userId } = state;
  if (
    !ctx.proxyPool?.canRotateSessions ||
    !ctx.isGoogleSearchUrl(tabState.lastRequestedUrl || '')
  ) {
    return;
  }

  const blocked = await ctx.isGoogleSearchBlocked(tabState.page);
  const unavailable = !blocked && (await ctx.isGoogleUnavailable(tabState.page));
  if (!blocked && !unavailable) return;

  const rotated = await ctx.rotateGoogleTab(
    userId,
    found.listItemId,
    req.params.tabId,
    tabState,
    blocked
      ? 'google_search_block_snapshot'
      : 'google_search_unavailable_snapshot',
    req.reqId,
  );
  if (rotated) copyRotatedTabState(tabState, rotated);
}

async function googleSerpSnapshot(req, ctx, tabState, pageUrl) {
  const { refs: googleRefs, snapshot: googleSnapshot } =
    await ctx.extractGoogleSerp(tabState.page);
  tabState.refs = googleRefs;
  tabState.lastSnapshot = googleSnapshot;
  ctx.snapshotBytes
    .labels('google_serp')
    .observe(Buffer.byteLength(googleSnapshot, 'utf8'));
  const win = ctx.windowSnapshot(googleSnapshot, 0);
  const response = buildWindowResponse(tabState, win, pageUrl);
  return attachScreenshot(req, response, tabState);
}

function annotateSnapshot(ctx, tabState, ariaYaml) {
  let annotatedYaml = ariaYaml || '';
  if (!annotatedYaml || tabState.refs.size === 0) return annotatedYaml;

  const refsByKey = new Map();
  for (const [refId, info] of tabState.refs) {
    const key = `${info.role}:${info.name}:${info.nth}`;
    refsByKey.set(key, refId);
  }

  const annotationCounts = new Map();
  return annotatedYaml
    .split('\n')
    .map((line) => {
      const match = line.match(/^(\s*-\s+)(\w+)(\s+"([^"]*)")?(.*)$/);
      if (!match) return line;

      const [, prefix, role, nameMatch, name, suffix] = match;
      const normalizedRole = role.toLowerCase();
      if (normalizedRole === 'combobox') return line;
      if (name && ctx.skipPatterns.some((pattern) => pattern.test(name))) {
        return line;
      }
      if (!ctx.interactiveRoles.includes(normalizedRole)) return line;

      const normalizedName = name || '';
      const countKey = `${normalizedRole}:${normalizedName}`;
      const nth = annotationCounts.get(countKey) || 0;
      annotationCounts.set(countKey, nth + 1);
      const key = `${normalizedRole}:${normalizedName}:${nth}`;
      const refId = refsByKey.get(key);
      if (!refId) return line;
      return `${prefix}${role}${nameMatch || ''} [${refId}]${suffix}`;
    })
    .join('\n');
}

async function freshSnapshot(req, ctx, state) {
  const { found, tabState, userId } = state;
  await rotateBlockedGoogleTab(req, ctx, { found, tabState, userId });

  const pageUrl = tabState.page.url();
  if (ctx.isGoogleSerp(pageUrl)) {
    return googleSerpSnapshot(req, ctx, tabState, pageUrl);
  }

  tabState.refs = await ctx.refreshTabRefs(tabState, { reason: 'snapshot' });
  const annotatedYaml = annotateSnapshot(
    ctx,
    tabState,
    await ctx.getAriaSnapshot(tabState.page),
  );

  tabState.lastSnapshot = annotatedYaml;
  if (annotatedYaml) {
    ctx.snapshotBytes
      .labels('full')
      .observe(Buffer.byteLength(annotatedYaml, 'utf8'));
  }
  const win = ctx.windowSnapshot(annotatedYaml, 0);
  const response = buildWindowResponse(tabState, win, tabState.page.url());
  return attachScreenshot(req, response, tabState);
}

/**
 * @openapi
 * /tabs/{tabId}/snapshot:
 *   get:
 *     tags: [Content]
 *     summary: Accessibility snapshot
 *     description: Returns accessibility tree with element refs. Supports pagination via offset.
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
 *       - name: format
 *         in: query
 *         schema:
 *           type: string
 *           enum: [text, json]
 *           default: text
 *       - name: offset
 *         in: query
 *         schema:
 *           type: integer
 *         description: Character offset for paginated retrieval.
 *       - name: includeScreenshot
 *         in: query
 *         schema:
 *           type: string
 *           enum: ['true', 'false']
 *     responses:
 *       200:
 *         description: Snapshot.
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 url:
 *                   type: string
 *                 snapshot:
 *                   type: string
 *                 refsCount:
 *                   type: integer
 *                 truncated:
 *                   type: boolean
 *                 totalChars:
 *                   type: integer
 *                 hasMore:
 *                   type: boolean
 *                 nextOffset:
 *                   type: integer
 *       404:
 *         description: Tab not found.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
export function mountTabSnapshotRoutes(app, ctx) {
  app.get('/tabs/:tabId/snapshot', async (req, res) => {
    try {
      const userId = req.query.userId;
      if (!userId) return res.status(400).json({ error: 'userId required' });
      const offset = parseInt(req.query.offset) || 0;
      const session = ctx.sessions.get(ctx.normalizeUserId(userId));
      const found = session && ctx.findTab(session, req.params.tabId);
      if (!found) return res.status(404).json({ error: 'Tab not found' });

      const { tabState } = found;
      tabState.toolCalls++;
      tabState.consecutiveTimeouts = 0;
      tabState.consecutiveFailures = 0;

      if (offset > 0 && tabState.lastSnapshot) {
        const win = ctx.windowSnapshot(tabState.lastSnapshot, offset);
        const response = buildWindowResponse(
          tabState,
          win,
          tabState.page.url(),
        );
        await attachScreenshot(req, response, tabState);
        ctx.log('info', 'snapshot (cached offset)', {
          reqId: req.reqId,
          tabId: req.params.tabId,
          offset,
          totalChars: win.totalChars,
        });
        return res.json(response);
      }

      const result = await ctx.withUserLimit(userId, () =>
        ctx.withTimeout(
          freshSnapshot(req, ctx, { found, tabState, userId }),
          ctx.requestTimeoutMs(),
          'snapshot',
        ),
      );

      ctx.pluginEvents.emit('tab:snapshot', {
        userId: req.query.userId,
        tabId: req.params.tabId,
        snapshot: result.snapshot,
      });
      ctx.log('info', 'snapshot', {
        reqId: req.reqId,
        tabId: req.params.tabId,
        url: result.url,
        snapshotLen: result.snapshot?.length,
        refsCount: result.refsCount,
        hasScreenshot: !!result.screenshot,
        truncated: result.truncated,
      });
      res.json(result);
    } catch (err) {
      ctx.log('error', 'snapshot failed', {
        reqId: req.reqId,
        tabId: req.params.tabId,
        error: err.message,
      });
      ctx.handleRouteError(err, req, res);
    }
    return undefined;
  });
}
