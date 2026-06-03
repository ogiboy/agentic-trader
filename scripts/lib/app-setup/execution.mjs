import { runLifecycleCommand } from '../app-lifecycle.mjs';
import { nextCommands, safetyNotes, setupPlan } from './plan.mjs';

function plannedStep(step) {
  return {
    ...step,
    status: step.selected ? 'planned' : 'deferred',
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
  const completed = runLifecycleCommand(step.command);
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
  const requestedMutation = options.core && options.yes && !options.dryRun;
  const dryRun = !requestedMutation;
  const results = [];
  let exitCode = 0;
  let attemptedMutation = false;
  let previousFailure = false;

  for (const step of setupPlan()) {
    if (!step.selected || dryRun) {
      results.push(plannedStep(step));
      continue;
    }
    if (previousFailure) {
      results.push(skippedStep(step, 'A previous core setup step failed.'));
      continue;
    }
    attemptedMutation = true;
    const result = runStep(step);
    results.push(result);
    if (result.exit_code !== 0) {
      previousFailure = true;
      exitCode = 1;
    }
  }

  return {
    payload: {
      action: 'setup',
      mode: options.core ? 'core' : 'plan',
      dry_run: dryRun,
      mutated: attemptedMutation,
      approved: options.yes,
      safety_notes: safetyNotes(),
      steps: results,
      next_commands: nextCommands(),
    },
    exitCode,
  };
}
