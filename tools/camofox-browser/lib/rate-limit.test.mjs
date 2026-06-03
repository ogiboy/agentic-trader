import assert from 'node:assert/strict';
import test from 'node:test';

import { rateLimit } from './rate-limit.js';

function createResponse() {
  return {
    body: null,
    headers: new Map(),
    statusCode: 200,
    set(name, value) {
      this.headers.set(name, value);
      return this;
    },
    status(code) {
      this.statusCode = code;
      return this;
    },
    json(payload) {
      this.body = payload;
      return this;
    },
  };
}

test('rateLimit blocks requests above the configured window limit', () => {
  let nowMs = 1_000;
  let nextCalls = 0;
  const middleware = rateLimit({
    windowMs: 10_000,
    max: 2,
    keyPrefix: 'test',
    keyGenerator: (req) => req.user,
    now: () => nowMs,
  });
  const req = { user: 'operator' };

  for (let index = 0; index < 2; index += 1) {
    const res = createResponse();
    middleware(req, res, () => {
      nextCalls += 1;
    });
    assert.equal(res.statusCode, 200);
  }

  const blocked = createResponse();
  middleware(req, blocked, () => {
    nextCalls += 1;
  });

  assert.equal(nextCalls, 2);
  assert.equal(blocked.statusCode, 429);
  assert.equal(blocked.headers.get('Retry-After'), '10');
  assert.deepEqual(blocked.body, { error: 'Too many requests' });

  nowMs += 10_000;
  const afterReset = createResponse();
  middleware(req, afterReset, () => {
    nextCalls += 1;
  });
  assert.equal(afterReset.statusCode, 200);
  assert.equal(nextCalls, 3);
});
