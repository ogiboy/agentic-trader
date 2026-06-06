export function usage(exitCode = 0) {
  process.stdout.write(`Usage: node scripts/app-doctor.mjs [options]

Read setup, provider, V1 readiness, and app-owned service status without
installing dependencies, starting/stopping services, pulling models, opening a
browser, or starting a trading daemon.

Options:
  --json      Emit a machine-readable summary.
  -h, --help  Show this help.
`);
  process.exit(exitCode);
}

export function parseArgs(argv) {
  const options = { json: false };
  for (const arg of argv) {
    if (arg === '--') {
      continue;
    }
    if (arg === '--json') {
      options.json = true;
    } else if (arg === '-h' || arg === '--help') {
      usage(0);
    } else {
      process.stderr.write(`Unknown option: ${arg}\n`);
      usage(2);
    }
  }
  return options;
}
