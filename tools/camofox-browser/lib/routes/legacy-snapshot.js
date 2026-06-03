function snapshotResponse(targetId, tabState, win, url) {
  return {
    ok: true,
    format: 'aria',
    targetId,
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

function annotateLegacySnapshot(tabState, ariaYaml) {
  let annotatedYaml = ariaYaml || '';
  if (!annotatedYaml || tabState.refs.size === 0) return annotatedYaml;

  const refsByKey = new Map();
  for (const [refId, element] of tabState.refs) {
    const key = `${element.role}:${element.name || ''}`;
    if (!refsByKey.has(key)) refsByKey.set(key, refId);
  }

  return annotatedYaml
    .split('\n')
    .map((line) => {
      const match = line.match(/^(\s*)-\s+(\w+)(?:\s+"([^"]*)")?/);
      if (!match) return line;

      const [, , role, name] = match;
      const key = `${role}:${name || ''}`;
      const refId = refsByKey.get(key);
      if (!refId) return line;
      return line.replace(/^(\s*-\s+\w+)/, `$1 [${refId}]`);
    })
    .join('\n');
}

async function googleSerpSnapshot(req, ctx, targetId, tabState, pageUrl) {
  const { refs: googleRefs, snapshot: googleSnapshot } =
    await ctx.extractGoogleSerp(tabState.page);
  tabState.refs = googleRefs;
  tabState.lastSnapshot = googleSnapshot;
  ctx.snapshotBytes
    .labels('google_serp')
    .observe(Buffer.byteLength(googleSnapshot, 'utf8'));
  const win = ctx.windowSnapshot(googleSnapshot, 0);
  const response = snapshotResponse(targetId, tabState, win, pageUrl);
  return attachScreenshot(req, response, tabState);
}

/**
 * @openapi
 * /snapshot:
 *   get:
 *     tags: [Legacy]
 *     summary: Snapshot (OpenClaw format)
 *     description: Snapshot with targetId/userId as query params.
 *     deprecated: true
 *     parameters:
 *       - name: targetId
 *         in: query
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
 *       - name: offset
 *         in: query
 *         schema:
 *           type: integer
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
export function mountLegacySnapshotRoutes(app, ctx) {
  app.get('/snapshot', async (req, res) => {
    try {
      const { targetId, userId } = req.query;
      const offset = parseInt(req.query.offset) || 0;
      if (!userId) {
        return res.status(400).json({ error: 'userId is required' });
      }

      const session = ctx.sessions.get(ctx.normalizeUserId(userId));
      const found = session && ctx.findTab(session, targetId);
      if (!found) return res.status(404).json({ error: 'Tab not found' });

      const { tabState } = found;
      tabState.toolCalls++;
      tabState.consecutiveTimeouts = 0;
      tabState.consecutiveFailures = 0;

      if (offset > 0 && tabState.lastSnapshot) {
        const win = ctx.windowSnapshot(tabState.lastSnapshot, offset);
        const response = snapshotResponse(
          targetId,
          tabState,
          win,
          tabState.page.url(),
        );
        await attachScreenshot(req, response, tabState);
        return res.json(response);
      }

      const pageUrl = tabState.page.url();
      if (ctx.isGoogleSerp(pageUrl)) {
        const response = await googleSerpSnapshot(
          req,
          ctx,
          targetId,
          tabState,
          pageUrl,
        );
        return res.json(response);
      }

      tabState.refs = await ctx.buildRefs(tabState.page);
      const annotatedYaml = annotateLegacySnapshot(
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
      const response = snapshotResponse(
        targetId,
        tabState,
        win,
        tabState.page.url(),
      );
      await attachScreenshot(req, response, tabState);
      res.json(response);
    } catch (err) {
      ctx.log('error', 'openclaw snapshot failed', {
        reqId: req.reqId,
        error: err.message,
      });
      ctx.handleRouteError(err, req, res);
    }
    return undefined;
  });
}
