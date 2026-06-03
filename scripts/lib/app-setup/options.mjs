export function usage(exitCode = 0) {
  process.stdout.write(`Usage: node scripts/app-setup.mjs [options]

Plan or run the conservative setup lifecycle slice.

Default behavior is a dry-run plan. The only mutating path implemented in this
slice is explicit core dependency repair with --core --yes.

Options:
  --core      Select root Node workspace and root uv Python repair.
  --yes       Approve the selected mutating setup scope.
  --dry-run   Print the setup plan without running mutating commands.
  --json      Emit a machine-readable summary.
  -h, --help  Show this help.
`);
  process.exit(exitCode);
}

export function parseArgs(argv) {
  const options = {
    core: false,
    dryRun: false,
    json: false,
    yes: false,
  };
  for (const arg of argv) {
    if (arg === '--') {
      continue;
    } else if (arg === '--core') {
      options.core = true;
    } else if (arg === '--dry-run') {
      options.dryRun = true;
    } else if (arg === '--json') {
      options.json = true;
    } else if (arg === '--yes') {
      options.yes = true;
    } else if (arg === '-h' || arg === '--help') {
      usage(0);
    } else {
      process.stderr.write(`Unknown option: ${arg}\n`);
      usage(2);
    }
  }
  if (options.yes && !options.core && !options.dryRun) {
    process.stderr.write(
      'The current app:setup slice requires --core before --yes can mutate setup.\n',
    );
    usage(2);
  }
  return options;
}
