import assert from 'node:assert/strict';
import test from 'node:test';

import { expandMacro, getSupportedMacros } from './macros.js';

test('expandMacro expands only supported macro keys', () => {
  assert.equal(
    expandMacro('@google_search', 'agentic trader'),
    'https://www.google.com/search?q=agentic%20trader',
  );
  assert.equal(expandMacro('@reddit_subreddit', ''), 'https://www.reddit.com/r/all.json?limit=25');
});

test('expandMacro rejects unsupported or inherited property names', () => {
  assert.equal(expandMacro('__proto__', 'ignored'), null);
  assert.equal(expandMacro('constructor', 'ignored'), null);
  assert.equal(expandMacro('@unknown', 'ignored'), null);
});

test('getSupportedMacros returns the explicit allowlist', () => {
  assert.ok(getSupportedMacros().includes('@google_search'));
  assert.equal(getSupportedMacros().includes('__proto__'), false);
});
