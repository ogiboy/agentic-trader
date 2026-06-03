import { runLifecycleCommand } from '../app-lifecycle.mjs';
import {
  nextCommands,
  safetyNotes,
  selectSteps,
  selectedScopesList,
  updatePlan,
} from './plan.mjs';

function plannedStep(step, selectedScopes) {
  return {
    ...step,
    status: selectedScopes.size === 0 || step.selected ? 'planned' : 'deferred',
    exit_code: null,
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

function runStep(step) {
  const completed = runLifecycleCommand(step.command, { cwd: step.cwd });
  return {
    ...step,
    status: completed.status === 0 ? 'passed' : 'failed',
    exit_code: completed.status ?? 1,
    spawn_error: completed.error,
    stdout: completed.stdout,
    stderr: completed.stderr,
  };
}

export function buildPayload(options) {
  const selectedScopes = options.selectedScopes;
  const dryRun = !(options.yes && !options.dryRun);
  const plan = selectSteps(updatePlan(), selectedScopes);
  const steps = [];
  let exitCode = 0;
  let mutated = false;
  let previousFailure = false;

  for (const step of plan) {
    if (dryRun || !step.selected) {
      steps.push(plannedStep(step, selectedScopes));
      continue;
    }
    if (previousFailure) {
      steps.push(skippedStep(step, 'A previous selected update step failed.'));
      continue;
    }
    const result = runStep(step);
    steps.push(result);
    mutated = mutated || step.mutates;
    if (result.exit_code !== 0) {
      previousFailure = true;
      exitCode = 1;
    }
  }

  return {
    payload: {
      action: 'update',
      mode: 'scoped',
      dry_run: dryRun,
      approved: options.yes,
      mutated,
      selected_scopes: selectedScopesList(selectedScopes),
      safety_notes: safetyNotes(),
      steps,
      next_commands: nextCommands(),
    },
    exitCode,
  };
}
