#!/usr/bin/env node
import { buildPayload } from './lib/app-uninstall/execution.mjs';
import { parseArgs } from './lib/app-uninstall/options.mjs';
import { renderHuman } from './lib/app-uninstall/render.mjs';

function main() {
  const options = parseArgs(process.argv.slice(2));
  const { payload, exitCode } = buildPayload(options);
  if (options.json) {
    process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
  } else {
    renderHuman(payload);
  }
  process.exit(exitCode);
}

main();
