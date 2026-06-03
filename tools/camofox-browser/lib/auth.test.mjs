import assert from 'node:assert/strict';
import test from 'node:test';

import { extractBearerToken } from './auth.js';

test('extractBearerToken accepts bearer tokens without regex parsing', () => {
  assert.equal(extractBearerToken('Bearer secret-token'), 'secret-token');
  assert.equal(extractBearerToken('   bearer\tsecret-token   '), 'secret-token');
});

test('extractBearerToken rejects missing or malformed bearer headers', () => {
  assert.equal(extractBearerToken('Basic secret-token'), null);
  assert.equal(extractBearerToken('Bearer'), null);
  assert.equal(extractBearerToken('Bearer    '), null);
  assert.equal(extractBearerToken('BearerToken secret-token'), null);
});
