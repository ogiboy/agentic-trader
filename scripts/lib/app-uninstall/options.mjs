export const SCOPE_IDS = ['artifacts', 'deps', 'service-state'];

export function usage(exitCode = 0) {
  process.stdout.write(`Usage: node scripts/app-uninstall.mjs [options]

Plan or run the conservative app-owned uninstall lifecycle slice.

Default behavior is a dry-run plan. Removing local files requires selecting one
or more scopes plus --yes.

Options:
  --artifacts      Remove generated build, test, and cache artifacts.
  --deps           Remove local dependency directories and local pnpm store.
  --service-state  Remove app-owned service log/state directories only when no
                   recorded service state file remains.
  --all            Select every uninstall scope.
  --yes            Approve the selected uninstall action.
  --dry-run        Print the uninstall plan without removing files.
  --json           Emit a machine-readable summary.
  -h, --help       Show this help.
`);
  process.exit(exitCode);
}

export function parseArgs(argv) {
  const options = {
    dryRun: false,
    json: false,
    selectedScopes: new Set(),
    yes: false,
  };

  for (const arg of argv) {
    if (arg === '--') {
      continue;
    } else if (arg === '--artifacts') {
      options.selectedScopes.add('artifacts');
    } else if (arg === '--deps') {
      options.selectedScopes.add('deps');
    } else if (arg === '--service-state') {
      options.selectedScopes.add('service-state');
    } else if (arg === '--all') {
      for (const scope of SCOPE_IDS) {
        options.selectedScopes.add(scope);
      }
    } else if (arg === '--yes') {
      options.yes = true;
    } else if (arg === '--dry-run') {
      options.dryRun = true;
    } else if (arg === '--json') {
      options.json = true;
    } else if (arg === '-h' || arg === '--help') {
      usage(0);
    } else {
      process.stderr.write(`Unknown option: ${arg}\n`);
      usage(2);
    }
  }

  if (options.yes && !options.dryRun && options.selectedScopes.size === 0) {
    process.stderr.write(
      'Select at least one uninstall scope before using --yes.\n',
    );
    usage(2);
  }

  return options;
}
