import assert from 'node:assert/strict';
import test from 'node:test';
import express from 'express';

import { mountSessionRoutes } from './routes/sessions.js';

function createCookieImportApp() {
  const app = express();
  const calls = { getSession: 0 };

  mountSessionRoutes(app, {
    closeSession: async () => {},
    config: {
      apiKey: 'secret-token',
      nodeEnv: 'production',
    },
    failuresTotal: {
      labels: () => ({
        inc: () => {},
      }),
    },
    getSession: async () => {
      calls.getSession += 1;
      return {
        context: {
          addCookies: async () => {},
        },
      };
    },
    handleRouteError: (_err, _req, res) => {
      res.status(500).json({ error: 'route error' });
    },
    log: () => {},
    normalizeUserId: (userId) => String(userId),
    pluginEvents: {
      emit: () => {},
    },
    safeError: (err) => err.message,
    scheduleBrowserIdleShutdown: () => {},
    sessions: new Map(),
  });

  return { app, calls };
}

async function postCookies(baseUrl, userId) {
  return fetch(`${baseUrl}/sessions/${userId}/cookies`, {
    body: JSON.stringify({ cookies: [] }),
    headers: {
      Authorization: 'Bearer secret-token',
      'Content-Type': 'application/json',
    },
    method: 'POST',
  });
}

test('cookie import route rate-limits authenticated requests', async () => {
  const { app, calls } = createCookieImportApp();
  const server = app.listen(0);

  try {
    const { port } = server.address();
    const baseUrl = `http://127.0.0.1:${port}`;

    for (let index = 0; index < 30; index += 1) {
      const response = await postCookies(baseUrl, 'operator');
      assert.equal(response.status, 200);
      assert.deepEqual(await response.json(), {
        ok: true,
        userId: 'operator',
        count: 0,
      });
    }

    const blocked = await postCookies(baseUrl, 'operator');
    assert.equal(blocked.status, 429);
    assert.equal(calls.getSession, 30);
  } finally {
    await new Promise((resolve, reject) => {
      server.close((err) => (err ? reject(err) : resolve()));
    });
  }
});
