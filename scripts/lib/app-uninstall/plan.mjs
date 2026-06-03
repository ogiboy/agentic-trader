import { existsSync } from 'node:fs';

import { SCOPE_IDS } from './options.mjs';
import { discoverDynamicTargets } from './discovery.mjs';
import { staticTargets } from './static-targets.mjs';

export function uninstallPlan() {
  return [...staticTargets(), ...discoverDynamicTargets()];
}

export function safetyNotes() {
  return [
    'app:uninstall defaults to a dry-run plan.',
    'Removing files requires an explicit scope plus --yes.',
    'Only app-owned or generated local artifacts are in scope: build/test caches, dependency directories, repo-local pnpm store, and app-owned helper service state/log directories.',
    'User secrets, provider accounts, brokerage configuration, host-owned services, global tools, Keychain items, and trading proposal approvals are preserved.',
    'Recorded service state files block service-state removal; stop app-owned services first so live processes are not orphaned.',
  ];
}

export function selectTargets(plan, selectedScopes) {
  return plan.map((target) => ({
    ...target,
    selected: selectedScopes.has(target.scope),
  }));
}

export function selectedScopesList(selectedScopes) {
  return SCOPE_IDS.filter((scope) => selectedScopes.has(scope));
}

export function targetExists(target) {
  if (Array.isArray(target.paths)) {
    return target.paths.some((path) => existsSync(path));
  }
  return existsSync(target.path);
}

export function blockingFile(target) {
  return target.blocking_files.find((file) => existsSync(file.path)) ?? null;
}

export function nextCommands() {
  return [
    'pnpm run app:uninstall -- --dry-run',
    'pnpm run app:stop -- --all --yes',
    'pnpm run app:uninstall -- --artifacts --deps --service-state --yes',
    'pnpm run app:doctor',
  ];
}
