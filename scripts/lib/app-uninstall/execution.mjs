import { existsSync, rmSync, statSync } from 'node:fs';

import { assertSafeRoot, relativeTarget, ROOT_DIR } from './paths.mjs';
import {
  blockingFile,
  nextCommands,
  safetyNotes,
  selectTargets,
  selectedScopesList,
  targetExists,
  uninstallPlan,
} from './plan.mjs';

function plannedTarget(target, selectedScopes) {
  return {
    ...target,
    exists: targetExists(target),
    status:
      selectedScopes.size === 0 || target.selected ? 'planned' : 'deferred',
    exit_code: null,
    stdout: '',
    stderr: '',
  };
}

function skippedTarget(target, reason) {
  return {
    ...target,
    exists: targetExists(target),
    status: 'skipped',
    reason,
    exit_code: null,
    stdout: '',
    stderr: '',
  };
}

function blockedTarget(target, blocker) {
  return {
    ...target,
    exists: targetExists(target),
    status: 'blocked',
    reason: `Recorded service state file remains: ${blocker.relative_path}`,
    exit_code: 1,
    stdout: '',
    stderr: '',
  };
}

function removePath(path) {
  const stat = statSync(path);
  rmSync(path, { recursive: stat.isDirectory(), force: true });
}

function removeTargetGroup(target) {
  const removedPaths = [];
  for (const path of target.paths) {
    try {
      if (!existsSync(path)) {
        continue;
      }
      removePath(path);
      removedPaths.push(relativeTarget(path));
    } catch (error) {
      return {
        ...target,
        exists: false,
        status: 'failed',
        exit_code: 1,
        stdout: '',
        stderr: error.message,
      };
    }
  }
  return {
    ...target,
    exists: removedPaths.length > 0,
    status: removedPaths.length > 0 ? 'removed' : 'missing',
    removed_paths: removedPaths,
    exit_code: 0,
    stdout: '',
    stderr: '',
  };
}

function removeTarget(target) {
  if (Array.isArray(target.paths)) {
    return removeTargetGroup(target);
  }

  try {
    if (!targetExists(target)) {
      return {
        ...target,
        exists: false,
        status: 'missing',
        exit_code: 0,
        stdout: '',
        stderr: '',
      };
    }

    removePath(target.path);
    return {
      ...target,
      exists: true,
      status: 'removed',
      exit_code: 0,
      stdout: '',
      stderr: '',
    };
  } catch (error) {
    return {
      ...target,
      exists: targetExists(target),
      status: 'failed',
      exit_code: 1,
      stdout: '',
      stderr: error.message,
    };
  }
}

export function buildPayload(options) {
  assertSafeRoot(ROOT_DIR);
  const selectedScopes = options.selectedScopes;
  const dryRun = !(options.yes && !options.dryRun);
  const plan = selectTargets(uninstallPlan(), selectedScopes);
  const targets = [];
  let exitCode = 0;
  let mutated = false;
  let previousFailure = false;

  for (const target of plan) {
    if (dryRun || !target.selected) {
      targets.push(plannedTarget(target, selectedScopes));
      continue;
    }
    if (previousFailure) {
      targets.push(
        skippedTarget(
          target,
          'A previous selected uninstall target failed or was blocked.',
        ),
      );
      continue;
    }

    const blocker = blockingFile(target);
    if (blocker) {
      targets.push(blockedTarget(target, blocker));
      previousFailure = true;
      exitCode = 1;
      continue;
    }

    const result = removeTarget(target);
    targets.push(result);
    mutated = mutated || result.status === 'removed';
    if (result.exit_code !== 0) {
      previousFailure = true;
      exitCode = result.exit_code;
    }
  }

  return {
    payload: {
      action: 'uninstall',
      mode: 'scoped',
      root: ROOT_DIR,
      dry_run: dryRun,
      approved: options.yes,
      mutated,
      selected_scopes: selectedScopesList(selectedScopes),
      safety_notes: safetyNotes(),
      targets,
      next_commands: nextCommands(),
    },
    exitCode,
  };
}
