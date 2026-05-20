import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import {
  ensureTracesDir,
  resolveTracePath,
  sweepOldTraces,
} from './tracing.js';

test('resolveTracePath only resolves zip trace names inside the user directory', () => {
  const baseDir = fs.mkdtempSync(path.join(os.tmpdir(), 'camofox-traces-'));
  try {
    assert.equal(resolveTracePath(baseDir, 'operator', 'trace.txt'), null);
    assert.equal(resolveTracePath(baseDir, 'operator', '../trace.zip'), null);
    assert.equal(resolveTracePath(baseDir, 'operator', '.trace.zip'), null);
    assert.match(
      resolveTracePath(baseDir, 'operator', 'trace-ok.zip'),
      /trace-ok\.zip$/,
    );
  } finally {
    fs.rmSync(baseDir, { recursive: true, force: true });
  }
});

test('sweepOldTraces honors zero ttl and size thresholds', () => {
  const baseDir = fs.mkdtempSync(path.join(os.tmpdir(), 'camofox-traces-'));
  try {
    const traceDir = ensureTracesDir(baseDir, 'operator');
    const tracePath = path.join(traceDir, 'trace-zero-threshold.zip');
    fs.writeFileSync(tracePath, 'x');

    const result = sweepOldTraces({
      baseDir,
      ttlMs: 0,
      maxBytesPerFile: 0,
      now: Date.now() + 1,
    });

    assert.equal(result.scanned, 1);
    assert.equal(result.removedTtl, 1);
    assert.equal(fs.existsSync(tracePath), false);
  } finally {
    fs.rmSync(baseDir, { recursive: true, force: true });
  }
});

test('sweepOldTraces ignores symlinked user trace directories', (t) => {
  const baseDir = fs.mkdtempSync(path.join(os.tmpdir(), 'camofox-traces-'));
  const outsideDir = fs.mkdtempSync(path.join(os.tmpdir(), 'camofox-outside-'));
  try {
    const outsideTrace = path.join(outsideDir, 'trace-outside.zip');
    fs.writeFileSync(outsideTrace, 'x');
    try {
      fs.symlinkSync(outsideDir, path.join(baseDir, 'linked-user'), 'dir');
    } catch (err) {
      t.skip(`symlink unavailable: ${err.message}`);
      return;
    }

    const result = sweepOldTraces({
      baseDir,
      ttlMs: 0,
      now: Date.now() + 1,
    });

    assert.equal(result.scanned, 0);
    assert.equal(fs.existsSync(outsideTrace), true);
  } finally {
    fs.rmSync(baseDir, { recursive: true, force: true });
    fs.rmSync(outsideDir, { recursive: true, force: true });
  }
});
