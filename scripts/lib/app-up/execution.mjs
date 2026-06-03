import {
  parseJsonPayload,
  persistToolOwnership,
  readToolOwnership,
  runLifecycleCommand,
} from '../app-lifecycle.mjs';
import { ownerBlocker, ownershipDecisions, ownershipUpdates } from './ownership.mjs';
import {
  nextCommands,
  safetyNotes,
  selectSteps,
  selectedScopesList,
  upPlan,
} from './plan.mjs';

function plannedStep(step, selectedScopes, owners) {
  const blocker = step.selected ? ownerBlocker(step, owners) : null;
  return {
    ...step,
    status: blocker ? 'blocked' : step.selected ? 'planned' : 'deferred',
    reason: blocker ?? step.reason,
    exit_code: blocker ? 1 : null,
    stdout: '',
    stderr: '',
  };
}

function skippedStep(step, reason) {
  return {
    ...step,
    status: 'skipped',
    reason,
    exit_code: null,
    stdout: '',
    stderr: '',
  };
}

function blockedStep(step, reason) {
  return {
    ...step,
    status: 'blocked',
    reason,
    exit_code: 1,
    stdout: '',
    stderr: '',
  };
}

function runStep(step) {
  const completed = runLifecycleCommand(step.command, { cwd: step.cwd });
  const payload =
    completed.status === 0 ? parseJsonPayload(completed.stdout) : null;
  return {
    ...step,
    status: completed.status === 0 ? 'passed' : 'failed',
    exit_code: completed.status ?? 1,
    payload,
    stdout: completed.stdout,
    stderr: completed.stderr,
  };
}

function stepSummary(steps) {
  const bucket = (step) => ({
    id: step.id,
    label: step.label,
    reason:
      step.reason ||
      (step.status === 'deferred'
        ? `Not selected; pass --${step.scope} to include this step.`
        : ''),
  });
  return {
    done: steps.filter((step) => step.status === 'passed').map(bucket),
    not_done: steps
      .filter((step) => ['blocked', 'failed', 'skipped'].includes(step.status))
      .map(bucket),
    deferred: steps.filter((step) => step.status === 'deferred').map(bucket),
  };
}

function ownershipStateFor(options, dryRun) {
  if (dryRun) {
    return { mutated: false, payload: readToolOwnership() };
  }
  return persistToolOwnership(ownershipUpdates(options), 'app-up');
}

export function buildPayload(options) {
  const selectedScopes = options.selectedScopes;
  const dryRun = !(options.yes && !options.dryRun);
  const plan = selectSteps(upPlan(options), selectedScopes);
  const ownershipState = ownershipStateFor(options, dryRun);
  const steps = [];
  let exitCode = 0;
  let mutated = ownershipState.mutated;
  let previousFailure = false;

  for (const step of plan) {
    if (dryRun || !step.selected) {
      const planned = plannedStep(step, selectedScopes, options.owners);
      steps.push(planned);
      if (!dryRun && step.selected && planned.status === 'blocked') {
        exitCode = 1;
        previousFailure = true;
      }
      continue;
    }

    if (previousFailure) {
      steps.push(
        skippedStep(
          step,
          'A previous selected app:up step failed or was blocked.',
        ),
      );
      continue;
    }

    const blocker = ownerBlocker(step, options.owners);
    if (blocker) {
      steps.push(blockedStep(step, blocker));
      previousFailure = true;
      exitCode = 1;
      continue;
    }

    const result = runStep(step);
    steps.push(result);
    mutated = mutated || (step.mutates && result.exit_code === 0);
    if (result.exit_code !== 0) {
      previousFailure = true;
      exitCode = 1;
    }
  }

  return {
    payload: {
      action: 'up',
      mode: 'guided-first-run',
      dry_run: dryRun,
      approved: options.yes,
      mutated,
      selected_scopes: selectedScopesList(selectedScopes),
      ownership_decisions: ownershipDecisions(options),
      tool_ownership: ownershipState.payload,
      open_browser: options.openBrowser,
      safety_notes: safetyNotes(),
      steps,
      summary: stepSummary(steps),
      next_commands: nextCommands(),
    },
    exitCode,
  };
}
