import fs from 'node:fs';
import { rateLimit } from 'express-rate-limit';

import {
  deleteTrace,
  listUserTraces,
  resolveTracePath,
  statTrace,
} from '../tracing.js';

const traceRateLimiter = rateLimit({
  identifier: 'traces',
  limit: 60,
  windowMs: 60_000,
  legacyHeaders: false,
  standardHeaders: true,
});

/**
 * @openapi
 * /sessions/{userId}/traces:
 *   get:
 *     tags: [Sessions]
 *     summary: List trace files
 *     description: Returns all Playwright trace zip files for the given user session, sorted newest first.
 *     security:
 *       - BearerAuth: []
 *     parameters:
 *       - name: userId
 *         in: path
 *         required: true
 *         schema:
 *           type: string
 *         description: Session owner identifier.
 *     responses:
 *       200:
 *         description: Trace list.
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 traces:
 *                   type: array
 *                   items:
 *                     type: object
 *                     properties:
 *                       filename:
 *                         type: string
 *                       sizeBytes:
 *                         type: integer
 *                       createdAt:
 *                         type: number
 *                       modifiedAt:
 *                         type: number
 *       403:
 *         description: Forbidden.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 *       500:
 *         description: Server error.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
function mountListTracesRoute(app, ctx) {
  app.get(
    '/sessions/:userId/traces',
    ctx.authMiddleware(),
    traceRateLimiter,
    async (req, res) => {
      try {
        const userId = ctx.normalizeUserId(req.params.userId);
        const traces = await listUserTraces(ctx.tracesDir, userId);
        res.json({ traces });
      } catch (err) {
        ctx.log('error', 'list traces failed', { error: err.message });
        res.status(500).json({ error: err.message });
      }
    },
  );
}

/**
 * @openapi
 * /sessions/{userId}/traces/{filename}:
 *   get:
 *     tags: [Sessions]
 *     summary: Download a trace file
 *     description: Streams a Playwright trace zip for viewing in trace.playwright.dev.
 *     security:
 *       - BearerAuth: []
 *     parameters:
 *       - name: userId
 *         in: path
 *         required: true
 *         schema:
 *           type: string
 *         description: Session owner identifier.
 *       - name: filename
 *         in: path
 *         required: true
 *         schema:
 *           type: string
 *         description: Trace zip filename.
 *     responses:
 *       200:
 *         description: Trace zip stream.
 *         content:
 *           application/zip:
 *             schema:
 *               type: string
 *               format: binary
 *       400:
 *         description: Invalid filename.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 *       404:
 *         description: Trace not found.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 *       403:
 *         description: Forbidden.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 *       500:
 *         description: Server error.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
function mountDownloadTraceRoute(app, ctx) {
  app.get(
    '/sessions/:userId/traces/:filename',
    ctx.authMiddleware(),
    traceRateLimiter,
    async (req, res) => {
      try {
        const userId = ctx.normalizeUserId(req.params.userId);
        const full = resolveTracePath(
          ctx.tracesDir,
          userId,
          req.params.filename,
        );
        if (!full) return res.status(400).json({ error: 'invalid filename' });
        const st = await statTrace(full);
        if (!st) return res.status(404).json({ error: 'not found' });
        res.setHeader('Content-Type', 'application/zip');
        res.setHeader('Content-Length', String(st.size));
        const stream = fs.createReadStream(full);
        stream.on('error', () => {
          if (!res.headersSent) res.status(404).json({ error: 'not found' });
          else res.destroy();
        });
        stream.pipe(res);
      } catch (err) {
        ctx.log('error', 'stream trace failed', { error: err.message });
        res.status(500).json({ error: err.message });
      }
    },
  );
}

/**
 * @openapi
 * /sessions/{userId}/traces/{filename}:
 *   delete:
 *     tags: [Sessions]
 *     summary: Delete a trace file
 *     description: Removes a specific Playwright trace zip from the server.
 *     security:
 *       - BearerAuth: []
 *     parameters:
 *       - name: userId
 *         in: path
 *         required: true
 *         schema:
 *           type: string
 *         description: Session owner identifier.
 *       - name: filename
 *         in: path
 *         required: true
 *         schema:
 *           type: string
 *         description: Trace zip filename.
 *     responses:
 *       200:
 *         description: Trace deleted.
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 ok:
 *                   type: boolean
 *       400:
 *         description: Invalid filename.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 *       404:
 *         description: Trace not found.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 *       403:
 *         description: Forbidden.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 *       500:
 *         description: Server error.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
function mountDeleteTraceRoute(app, ctx) {
  app.delete(
    '/sessions/:userId/traces/:filename',
    ctx.authMiddleware(),
    traceRateLimiter,
    async (req, res) => {
      try {
        const userId = ctx.normalizeUserId(req.params.userId);
        const full = resolveTracePath(
          ctx.tracesDir,
          userId,
          req.params.filename,
        );
        if (!full) return res.status(400).json({ error: 'invalid filename' });
        try {
          await deleteTrace(full);
        } catch (err) {
          if (err.code === 'ENOENT') {
            return res.status(404).json({ error: 'not found' });
          }
          throw err;
        }
        res.json({ ok: true });
      } catch (err) {
        ctx.log('error', 'delete trace failed', { error: err.message });
        res.status(500).json({ error: err.message });
      }
    },
  );
}

export function mountTraceRoutes(app, ctx) {
  mountListTracesRoute(app, ctx);
  mountDownloadTraceRoute(app, ctx);
  mountDeleteTraceRoute(app, ctx);
}
