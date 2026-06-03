import { readdirSync } from 'node:fs';
import { join } from 'node:path';

import { ROOT_DIR, relativeTarget } from './paths.mjs';
import { uninstallTargetGroup } from './target-factory.mjs';

function shouldPrune(path) {
  const rel = relativeTarget(path);
  return [
    '.git',
    '.venv',
    'node_modules',
    '.pnpm-store',
    'docs/node_modules',
    'docs/.next',
    'docs/out',
    'docs/.source',
    'webgui/node_modules',
    'webgui/.next',
    'webgui/out',
    'tui/node_modules',
    'tui/dist',
    'tools/camofox-browser/node_modules',
    'tools/camofox-browser/dist',
    'tools/camofox-browser/build',
    'tools/camofox-browser/coverage',
    'tools/camofox-browser/.cache',
    'tools/camofox-browser/test-results',
    'tools/camofox-browser/playwright-report',
    'sidecars/research_flow/.venv',
  ].includes(rel);
}

export function discoverDynamicTargets() {
  const pycachePaths = [];
  const eggInfoPaths = [];

  function walk(dir) {
    let entries;
    try {
      entries = readdirSync(dir, { withFileTypes: true });
    } catch {
      return;
    }

    for (const entry of entries) {
      const path = join(dir, entry.name);
      if (!entry.isDirectory() || shouldPrune(path)) {
        continue;
      }
      if (entry.name === '__pycache__') {
        pycachePaths.push(relativeTarget(path));
        continue;
      }
      walk(path);
    }
  }

  walk(ROOT_DIR);

  for (const entry of readdirSync(ROOT_DIR, { withFileTypes: true })) {
    if (entry.isDirectory() && entry.name.endsWith('.egg-info')) {
      eggInfoPaths.push(entry.name);
    }
  }

  const targets = [];
  if (pycachePaths.length > 0) {
    targets.push(
      uninstallTargetGroup(
        'python-bytecode-caches',
        'Python bytecode caches',
        pycachePaths,
        'artifacts',
      ),
    );
  }
  if (eggInfoPaths.length > 0) {
    targets.push(
      uninstallTargetGroup(
        'python-package-metadata',
        'Python package metadata directories',
        eggInfoPaths,
        'artifacts',
      ),
    );
  }
  return targets;
}
