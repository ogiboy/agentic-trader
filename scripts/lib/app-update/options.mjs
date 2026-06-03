export const SCOPE_IDS = ['core', 'sidecar', 'camofox', 'build', 'status'];

export function usage(exitCode = 0) {
  process.stdout.write(`Usage: node scripts/app-update.mjs [options]

Plan or run the app update lifecycle lane.

Default behavior is a dry-run plan. Mutating updates require selecting one or
more scopes plus --yes.

Options:
  --core     Update root pnpm workspace and root uv lock/env owners.
  --sidecar  Update the CrewAI Flow sidecar uv lock/env owner.
  --camofox  Update optional Camofox helper package dependencies only.
  --build    Run repository build/check validation after selected updates.
  --status   Run app:doctor after selected updates.
  --all      Select every update, build, and status scope.
  --yes      Approve selected update actions.
  --dry-run  Print the update plan without running commands.
  --json     Emit a machine-readable summary.
  -h, --help Show this help.
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
    } else if (arg === '--core') {
      options.selectedScopes.add('core');
    } else if (arg === '--sidecar') {
      options.selectedScopes.add('sidecar');
    } else if (arg === '--camofox') {
      options.selectedScopes.add('camofox');
    } else if (arg === '--build') {
      options.selectedScopes.add('build');
    } else if (arg === '--status') {
      options.selectedScopes.add('status');
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
      'Select at least one update scope before using --yes.\n',
    );
    usage(2);
  }

  return options;
}
