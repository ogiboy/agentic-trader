import {
  MAX_DOWNLOAD_INLINE_BYTES,
  clearTabDownloads,
  getDownloadsList,
} from '../downloads.js';
import { extractPageImages } from '../images.js';

function queryTab(req, ctx) {
  const userId = req.query.userId;
  const session = ctx.sessions.get(ctx.normalizeUserId(userId));
  const found = session && ctx.findTab(session, req.params.tabId);
  return { found, session, userId };
}

/**
 * @openapi
 * /tabs/{tabId}/links:
 *   get:
 *     tags: [Content]
 *     summary: Extract page links
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
 *         description: Links extracted.
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 links:
 *                   type: array
 *                   items:
 *                     type: object
 *                     properties:
 *                       text:
 *                         type: string
 *                       href:
 *                         type: string
 *                       ref:
 *                         type: string
 *       404:
 *         description: Tab not found.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
function mountLinksRoute(app, ctx) {
  app.get('/tabs/:tabId/links', async (req, res) => {
    try {
      const limit = parseInt(req.query.limit) || 50;
      const offset = parseInt(req.query.offset) || 0;
      const { found, session, userId } = queryTab(req, ctx);
      if (!found) {
        ctx.log('warn', 'links: tab not found', {
          reqId: req.reqId,
          tabId: req.params.tabId,
          userId,
          hasSession: !!session,
        });
        return res.status(404).json({ error: 'Tab not found' });
      }

      const { tabState } = found;
      tabState.toolCalls++;
      tabState.consecutiveTimeouts = 0;
      tabState.consecutiveFailures = 0;

      const allLinks = await tabState.page.evaluate(() => {
        const links = [];
        document.querySelectorAll('a[href]').forEach((a) => {
          const href = a.href;
          const text = a.textContent?.trim().slice(0, 100) || '';
          if (href && href.startsWith('http')) {
            links.push({ url: href, text });
          }
        });
        return links;
      });

      const total = allLinks.length;
      const paginated = allLinks.slice(offset, offset + limit);

      res.json({
        links: paginated,
        pagination: { total, offset, limit, hasMore: offset + limit < total },
      });
    } catch (err) {
      ctx.log('error', 'links failed', {
        reqId: req.reqId,
        error: err.message,
      });
      ctx.handleRouteError(err, req, res);
    }
  });
}

/**
 * @openapi
 * /tabs/{tabId}/downloads:
 *   get:
 *     tags: [Content]
 *     summary: List tab downloads
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
 *         description: Downloads list.
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 downloads:
 *                   type: array
 *                   items:
 *                     type: object
 *                     properties:
 *                       filename:
 *                         type: string
 *                       url:
 *                         type: string
 *                       state:
 *                         type: string
 *       404:
 *         description: Tab not found.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
function mountDownloadsRoute(app, ctx) {
  app.get('/tabs/:tabId/downloads', async (req, res) => {
    try {
      const includeData = req.query.includeData === 'true';
      const consume = req.query.consume === 'true';
      const maxBytesRaw = Number(req.query.maxBytes);
      const maxBytes =
        Number.isFinite(maxBytesRaw) && maxBytesRaw > 0
          ? maxBytesRaw
          : MAX_DOWNLOAD_INLINE_BYTES;
      const { found } = queryTab(req, ctx);
      if (!found) return res.status(404).json({ error: 'Tab not found' });

      const { tabState } = found;
      tabState.toolCalls++;

      const downloads = await getDownloadsList(tabState, {
        includeData,
        maxBytes,
      });

      if (consume) {
        await clearTabDownloads(tabState);
      }

      res.json({ tabId: req.params.tabId, downloads });
    } catch (err) {
      ctx.failuresTotal.labels(ctx.classifyError(err), 'downloads').inc();
      ctx.log('error', 'downloads failed', {
        reqId: req.reqId,
        error: err.message,
      });
      res.status(500).json({ error: ctx.safeError(err) });
    }
  });
}

/**
 * @openapi
 * /tabs/{tabId}/images:
 *   get:
 *     tags: [Content]
 *     summary: Extract page images
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
 *         description: Images extracted.
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 images:
 *                   type: array
 *                   items:
 *                     type: object
 *                     properties:
 *                       src:
 *                         type: string
 *                       alt:
 *                         type: string
 *                       width:
 *                         type: integer
 *                       height:
 *                         type: integer
 *       404:
 *         description: Tab not found.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
function mountImagesRoute(app, ctx) {
  app.get('/tabs/:tabId/images', async (req, res) => {
    try {
      const includeData = req.query.includeData === 'true';
      const maxBytesRaw = Number(req.query.maxBytes);
      const limitRaw = Number(req.query.limit);
      const maxBytes =
        Number.isFinite(maxBytesRaw) && maxBytesRaw > 0
          ? maxBytesRaw
          : MAX_DOWNLOAD_INLINE_BYTES;
      const limit =
        Number.isFinite(limitRaw) && limitRaw > 0
          ? Math.min(Math.floor(limitRaw), 20)
          : 8;
      const { found } = queryTab(req, ctx);
      if (!found) return res.status(404).json({ error: 'Tab not found' });

      const { tabState } = found;
      tabState.toolCalls++;

      const images = await extractPageImages(tabState.page, {
        includeData,
        maxBytes,
        limit,
      });

      res.json({ tabId: req.params.tabId, images });
    } catch (err) {
      ctx.failuresTotal.labels(ctx.classifyError(err), 'images').inc();
      ctx.log('error', 'images failed', {
        reqId: req.reqId,
        error: err.message,
      });
      res.status(500).json({ error: ctx.safeError(err) });
    }
  });
}

export function mountTabContentRoutes(app, ctx) {
  mountLinksRoute(app, ctx);
  mountDownloadsRoute(app, ctx);
  mountImagesRoute(app, ctx);
}
