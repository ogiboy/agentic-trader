import express from 'express';
import {
  extractDeterministic,
  validateSchema as validateExtractSchema,
} from '../extract.js';

function findMutableTab(req, ctx, userId, options = {}) {
  const session = ctx.sessions.get(ctx.normalizeUserId(userId));
  const found = session && ctx.findTab(session, req.params.tabId);
  if (!found) return null;

  session.lastAccess = Date.now();
  const { tabState } = found;
  tabState.toolCalls++;
  tabState.consecutiveTimeouts = 0;
  if (options.resetFailures) {
    tabState.consecutiveFailures = 0;
  }
  return { session, tabState };
}

/**
 * @openapi
 * /tabs/{tabId}/evaluate:
 *   post:
 *     tags: [Interaction]
 *     summary: Evaluate JavaScript in tab
 *     description: Runs arbitrary JS in the page context and returns the result.
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
 *             required: [userId, expression]
 *             properties:
 *               userId:
 *                 type: string
 *               expression:
 *                 type: string
 *                 description: JavaScript expression to evaluate.
 *     responses:
 *       200:
 *         description: Evaluation result.
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 ok:
 *                   type: boolean
 *                 result: {}
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
function mountEvaluateRoute(app, ctx) {
  app.post(
    '/tabs/:tabId/evaluate',
    express.json({ limit: '1mb' }),
    async (req, res) => {
      try {
        const { userId, expression } = req.body;
        if (!userId) {
          return res.status(400).json({ error: 'userId is required' });
        }
        if (!expression) {
          return res.status(400).json({ error: 'expression is required' });
        }

        const found = findMutableTab(req, ctx, userId, {
          resetFailures: true,
        });
        if (!found) return res.status(404).json({ error: 'Tab not found' });

        ctx.pluginEvents.emit('tab:evaluate', {
          userId,
          tabId: req.params.tabId,
          expression,
        });
        const result = await found.tabState.page.evaluate(expression);
        ctx.pluginEvents.emit('tab:evaluated', {
          userId,
          tabId: req.params.tabId,
          result,
        });
        ctx.log('info', 'evaluate', {
          reqId: req.reqId,
          tabId: req.params.tabId,
          userId,
          resultType: typeof result,
        });
        res.json({ ok: true, result });
      } catch (err) {
        ctx.failuresTotal.labels(ctx.classifyError(err), 'evaluate').inc();
        ctx.log('error', 'evaluate failed', {
          reqId: req.reqId,
          error: err.message,
        });
        res.status(500).json({ error: ctx.safeError(err) });
      }
    },
  );
}

/**
 * @openapi
 * /tabs/{tabId}/extract:
 *   post:
 *     tags: [Content]
 *     summary: Structured data extraction via JSON Schema
 *     description: |
 *       Extracts structured data from the current page using a JSON Schema whose properties
 *       carry `x-ref` hints pointing at snapshot element refs (e.g. `e1`, `e2`).
 *       Call `GET /tabs/{tabId}/snapshot` first to populate the ref table.
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
 *             required: [userId, schema]
 *             properties:
 *               userId:
 *                 type: string
 *               schema:
 *                 type: object
 *                 description: |
 *                   JSON Schema with `type: "object"` and a `properties` map.
 *                   Each property may include `x-ref` (a snapshot element ref) and an optional
 *                   `type` (`string`, `number`, `integer`, `boolean`).
 *                 required: [type, properties]
 *                 properties:
 *                   type:
 *                     type: string
 *                     enum: [object]
 *                   properties:
 *                     type: object
 *                     additionalProperties:
 *                       type: object
 *                       properties:
 *                         type:
 *                           type: string
 *                           enum: [string, number, integer, boolean, object, "null"]
 *                         x-ref:
 *                           type: string
 *                           description: Snapshot element ref (e.g. `e1`).
 *                   required:
 *                     type: array
 *                     items:
 *                       type: string
 *                     description: Property names that must resolve to a non-null value.
 *     responses:
 *       200:
 *         description: Extraction succeeded.
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 ok:
 *                   type: boolean
 *                 data:
 *                   type: object
 *                   description: Extracted key-value pairs matching the input schema.
 *       400:
 *         description: Missing userId, missing schema, or invalid schema.
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
 *       409:
 *         description: No refs available -- call snapshot first.
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 error:
 *                   type: string
 *                 snapshot:
 *                   type: string
 *                   nullable: true
 *       422:
 *         description: Extraction failed (e.g. required ref not found).
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 ok:
 *                   type: boolean
 *                 error:
 *                   type: string
 *                 snapshot:
 *                   type: string
 *                   nullable: true
 *       500:
 *         description: Internal server error.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
function mountExtractRoute(app, ctx) {
  app.post(
    '/tabs/:tabId/extract',
    express.json({ limit: '256kb' }),
    async (req, res) => {
      try {
        const { userId, schema } = req.body;
        if (!userId) {
          return res.status(400).json({ error: 'userId is required' });
        }
        if (!schema) {
          return res.status(400).json({ error: 'schema is required' });
        }

        const check = validateExtractSchema(schema);
        if (!check.ok) return res.status(400).json({ error: check.error });

        const found = findMutableTab(req, ctx, userId);
        if (!found) return res.status(404).json({ error: 'Tab not found' });

        const { tabState } = found;
        if (!tabState.refs || tabState.refs.size === 0) {
          return res.status(409).json({
            error:
              'no refs available -- call GET /tabs/:tabId/snapshot first to build the ref table',
            snapshot: tabState.lastSnapshot || null,
          });
        }

        try {
          const data = extractDeterministic({ schema, refs: tabState.refs });
          ctx.log('info', 'extract', {
            reqId: req.reqId,
            tabId: req.params.tabId,
            userId,
            keys: Object.keys(data),
          });
          res.json({ ok: true, data });
        } catch (extractErr) {
          ctx.log('warn', 'extract failed', {
            reqId: req.reqId,
            error: extractErr.message,
          });
          res.status(422).json({
            ok: false,
            error: extractErr.message,
            snapshot: tabState.lastSnapshot || null,
          });
        }
      } catch (err) {
        ctx.failuresTotal.labels(ctx.classifyError(err), 'extract').inc();
        ctx.log('error', 'extract error', {
          reqId: req.reqId,
          error: err.message,
        });
        res.status(500).json({ error: ctx.safeError(err) });
      }
    },
  );
}

export function mountTabEvaluationRoutes(app, ctx) {
  mountEvaluateRoute(app, ctx);
  mountExtractRoute(app, ctx);
}
