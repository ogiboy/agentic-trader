import {
  parseJsonPayload,
  resolveAgenticTrader,
  runLifecycleCommand,
} from '../app-lifecycle.mjs';
import { SERVICE_IDS } from './options.mjs';
import {
  nextCommands,
  ownerBlocker,
  safetyNotes,
  startPlan,
  stopPlan,
} from './plan.mjs';

function plannedStep(step, mode) {
  const blocker = step.selected ? ownerBlocker(step, mode) : null;
  return {
    ...step,
    status: blocker ? 'blocked' : step.selected ? 'planned' : 'deferred',
    reason: blocker ?? step.reason,
    exit_code: blocker ? 1 : null,
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

function commandSucceeded(mode, payload, step = null) {
  if (!payload || typeof payload !== 'object') {
    return false;
  }
  if (mode === 'start') {
    if (
      step?.id === 'webgui-service' &&
      payload.app_owned === false &&
      payload.service_reachable === true
    ) {
      return true;
    }
    return payload.app_owned === true;
  }
  return payload.app_owned !== true;
}

function runStep(cliPath, step, mode) {
  const completed = runLifecycleCommand([cliPath, ...step.command.slice(1)]);
  const payload =
    completed.status === 0 ? parseJsonPayload(completed.stdout) : null;
  const passed =
    completed.status === 0 && commandSucceeded(mode, payload, step);
  return {
    ...step,
    resolved_command: [cliPath, ...step.command.slice(1)],
    status: passed ? 'passed' : 'failed',
    exit_code: completed.status ?? 1,
    payload,
    stdout: completed.stdout,
    stderr: completed.stderr,
  };
}

export function buildPayload(options) {
  const dryRun = !(options.yes && !options.dryRun);
  const cliPath = resolveAgenticTrader();
  const plan =
    options.mode === 'start' ? startPlan(options) : stopPlan(options);
  const selectedServices = SERVICE_IDS.filter((serviceId) =>
    options.selectedServices.has(serviceId),
  );
  const results = [];
  let exitCode = 0;
  let attemptedMutation = false;
  let previousFailure = false;

  for (const step of plan) {
    if (!step.selected || dryRun) {
      const planned = plannedStep(step, options.mode);
      results.push(planned);
      if (!dryRun && step.selected && planned.status === 'blocked') {
        exitCode = 1;
        previousFailure = true;
      }
      continue;
    }
    if (options.mode === 'start' && previousFailure) {
      results.push(skippedStep(step, 'A previous selected start step failed.'));
      continue;
    }
    const blocker = ownerBlocker(step, options.mode);
    if (blocker) {
      results.push(blockedStep(step, blocker));
      exitCode = 1;
      previousFailure = true;
      continue;
    }
    if (!cliPath) {
      results.push(
        blockedStep(
          step,
          'agentic-trader entrypoint was not found. Run make setup, then retry the lifecycle command.',
        ),
      );
      exitCode = 1;
      continue;
    }

    attemptedMutation = true;
    const result = runStep(cliPath, step, options.mode);
    results.push(result);
    if (result.status !== 'passed') {
      exitCode = 1;
      previousFailure = true;
    }
  }

  return {
    payload: {
      action: options.mode,
      mode: 'services',
      dry_run: dryRun,
      mutated: attemptedMutation,
      approved: options.yes,
      selected_services: selectedServices,
      cli_path: cliPath,
      open_browser: options.openBrowser,
      safety_notes: safetyNotes(options.mode, options),
      steps: results,
      next_commands: nextCommands(options, selectedServices),
    },
    exitCode,
  };
}
