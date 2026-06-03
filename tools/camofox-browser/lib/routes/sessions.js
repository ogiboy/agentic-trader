import express from 'express';
import { rateLimit } from 'express-rate-limit';

import {
  extractBearerToken,
  isLoopbackAddress,
  timingSafeCompare,
} from '../auth.js';
import { classifyError } from '../request-utils.js';

const cookieImportRateLimiter = rateLimit({
  identifier: 'cookie-import',
  limit: 30,
  windowMs: 60_000,
  legacyHeaders: false,
  standardHeaders: true,
});

function authorizeCookieImport(req, res, config) {
  if (config.apiKey) {
    const token = extractBearerToken(req.headers['authorization']);
    if (!token || !timingSafeCompare(token, config.apiKey)) {
      res.status(403).json({ error: 'Forbidden' });
      return false;
    }
    return true;
  }

  const remoteAddress = req.socket?.remoteAddress || '';
  const allowUnauthedLocal =
    config.nodeEnv !== 'production' && isLoopbackAddress(remoteAddress);
  if (!allowUnauthedLocal) {
    res.status(403).json({
      error:
        'Cookie import is disabled without CAMOFOX_API_KEY except for loopback requests in non-production environments.',
    });
    return false;
  }
  return true;
}

function validateCookies(cookies) {
  if (!Array.isArray(cookies)) {
    return { error: 'cookies must be an array' };
  }
  if (cookies.length > 500) {
    return { error: 'Too many cookies. Maximum 500 per request.' };
  }

  const invalid = [];
  for (let index = 0; index < cookies.length; index += 1) {
    const cookie = cookies[index];
    const missing = [];
    if (!cookie || typeof cookie !== 'object') {
      invalid.push({ index, error: 'cookie must be an object' });
      continue;
    }
    if (typeof cookie.name !== 'string' || !cookie.name) missing.push('name');
    if (typeof cookie.value !== 'string') missing.push('value');
    if (typeof cookie.domain !== 'string' || !cookie.domain) {
      missing.push('domain');
    }
    if (missing.length) invalid.push({ index, missing });
  }
  if (invalid.length) {
    return {
      error:
        'Invalid cookie objects: each cookie must include name, value, and domain',
      invalid,
    };
  }
  return null;
}

function sanitizeCookies(cookies) {
  const allowedFields = [
    'name',
    'value',
    'domain',
    'path',
    'expires',
    'httpOnly',
    'secure',
    'sameSite',
  ];
  return cookies.map((cookie) => {
    const clean = {};
    for (const field of allowedFields) {
      if (cookie[field] !== undefined) clean[field] = cookie[field];
    }
    return clean;
  });
}

/**
 * @openapi
 * /sessions/{userId}/cookies:
 *   post:
 *     tags: [Sessions]
 *     summary: Import cookies into a user session
 *     description: Import cookies for authenticated browsing. Requires BearerAuth in production.
 *     security:
 *       - BearerAuth: []
 *     parameters:
 *       - name: userId
 *         in: path
 *         required: true
 *         schema:
 *           type: string
 *         description: Session owner identifier.
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required: [cookies]
 *             properties:
 *               cookies:
 *                 type: array
 *                 maxItems: 500
 *                 items:
 *                   type: object
 *                   required: [name, value, domain]
 *                   properties:
 *                     name:
 *                       type: string
 *                     value:
 *                       type: string
 *                     domain:
 *                       type: string
 *                     path:
 *                       type: string
 *                     expires:
 *                       type: number
 *                     httpOnly:
 *                       type: boolean
 *                     secure:
 *                       type: boolean
 *                     sameSite:
 *                       type: string
 *                       enum: [Strict, Lax, None]
 *     responses:
 *       200:
 *         description: Cookies imported.
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 ok:
 *                   type: boolean
 *                 userId:
 *                   type: string
 *                 count:
 *                   type: integer
 *       400:
 *         description: Invalid cookie data.
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
 *       429:
 *         description: Too many cookie import requests.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
function mountCookieImportRoute(app, ctx) {
  app.post(
    '/sessions/:userId/cookies',
    cookieImportRateLimiter,
    express.json({ limit: '512kb' }),
    async (req, res) => {
      try {
        if (!authorizeCookieImport(req, res, ctx.config)) {
          return;
        }
        if (!req.body || !('cookies' in req.body)) {
          return res
            .status(400)
            .json({ error: 'Missing "cookies" field in request body' });
        }

        const validation = validateCookies(req.body.cookies);
        if (validation) {
          return res.status(400).json(validation);
        }

        const userId = req.params.userId;
        const sanitized = sanitizeCookies(req.body.cookies);
        const session = await ctx.getSession(userId);
        await session.context.addCookies(sanitized);
        ctx.log('info', 'cookies imported', {
          reqId: req.reqId,
          userId: String(userId),
          count: sanitized.length,
        });
        ctx.pluginEvents.emit('session:cookies:import', {
          userId: String(userId),
          count: sanitized.length,
        });
        res.json({
          ok: true,
          userId: String(userId),
          count: sanitized.length,
        });
      } catch (err) {
        ctx.failuresTotal.labels(classifyError(err), 'set_cookies').inc();
        ctx.log('error', 'cookie import failed', {
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
 * /sessions/{userId}:
 *   delete:
 *     tags: [Sessions]
 *     summary: Destroy a user session
 *     description: Closes all tabs and cleans up state for the given userId.
 *     parameters:
 *       - name: userId
 *         in: path
 *         required: true
 *         schema:
 *           type: string
 *     responses:
 *       200:
 *         description: Session destroyed.
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 ok:
 *                   type: boolean
 *                 closed:
 *                   type: integer
 *       404:
 *         description: Session not found.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
function mountDeleteSessionRoute(app, ctx) {
  app.delete('/sessions/:userId', async (req, res) => {
    try {
      const userId = ctx.normalizeUserId(req.params.userId);
      const session = ctx.sessions.get(userId);
      if (session) {
        await ctx.closeSession(userId, session, {
          reason: 'api_delete_session',
          clearDownloads: true,
          clearLocks: true,
        });
        ctx.log('info', 'session closed', { userId });
      }
      if (ctx.sessions.size === 0) ctx.scheduleBrowserIdleShutdown();
      res.json({ ok: true });
    } catch (err) {
      ctx.log('error', 'session close failed', { error: err.message });
      ctx.handleRouteError(err, req, res);
    }
  });
}

export function mountSessionRoutes(app, ctx) {
  mountCookieImportRoute(app, ctx);
  mountDeleteSessionRoute(app, ctx);
}
