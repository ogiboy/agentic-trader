#!/usr/bin/env node
import { resolveAgenticTrader } from './lib/app-lifecycle.mjs';
import { parseArgs } from './lib/app-doctor/options.mjs';
import { renderHuman } from './lib/app-doctor/rendering.mjs';
import { doctorSteps, runStep, safetyNotes } from './lib/app-doctor/steps.mjs';

function buildPayload(cliPath) {
  const steps = cliPath
    ? doctorSteps().map((stepInfo) => runStep(cliPath, stepInfo))
    : [];
  return {
    action: 'doctor',
    dry_run: false,
    mutated: false,
    cli_path: cliPath,
    safety_notes: safetyNotes(),
    steps,
  };
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  const payload = buildPayload(resolveAgenticTrader());
  const exitCode =
    payload.cli_path && payload.steps.every((result) => result.exit_code === 0)
      ? 0
      : 1;

  if (options.json) {
    process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
  } else {
    renderHuman(payload);
  }
  process.exit(exitCode);
}

main();
