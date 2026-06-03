export const SERVICE_IDS = [
  'model-service',
  'camofox-service',
  'webgui-service',
];

export function usage(exitCode = 0) {
  process.stdout
    .write(`Usage: node scripts/app-services.mjs <start|stop> [options]

Plan or run app-owned service lifecycle slices.

Default behavior is a dry-run plan. Mutating start/stop requires an explicit
service selection plus --yes.

Options:
  --webgui        Select the app-owned Web GUI service.
  --model-service Select the app-owned local model-service.
  --camofox-service Select the app-owned Camofox helper service.
  --all           Select all app-owned helper services.
  --yes           Approve the selected mutating service action.
  --dry-run       Print the service plan without starting or stopping services.
  --json          Emit a machine-readable summary.
  --open-browser  With start + webgui, ask the OS to open the Web GUI URL.
  -h, --help      Show this help.
`);
  process.exit(exitCode);
}

export function parseArgs(argv) {
  const [mode, ...rest] = argv.filter((arg) => arg !== '--');
  if (mode === '-h' || mode === '--help') {
    usage(0);
  }
  if (mode !== 'start' && mode !== 'stop') {
    process.stderr.write('Expected lifecycle mode: start or stop.\n');
    usage(2);
  }

  const options = {
    mode,
    dryRun: false,
    json: false,
    openBrowser: false,
    selectedServices: new Set(),
    yes: false,
  };

  for (const arg of rest) {
    if (arg === '--webgui') {
      options.selectedServices.add('webgui-service');
    } else if (arg === '--model-service') {
      options.selectedServices.add('model-service');
    } else if (arg === '--camofox-service') {
      options.selectedServices.add('camofox-service');
    } else if (arg === '--all') {
      for (const serviceId of SERVICE_IDS) {
        options.selectedServices.add(serviceId);
      }
    } else if (arg === '--dry-run') {
      options.dryRun = true;
    } else if (arg === '--json') {
      options.json = true;
    } else if (arg === '--open-browser') {
      options.openBrowser = true;
    } else if (arg === '--yes') {
      options.yes = true;
    } else if (arg === '-h' || arg === '--help') {
      usage(0);
    } else {
      process.stderr.write(`Unknown option: ${arg}\n`);
      usage(2);
    }
  }

  if (options.openBrowser && mode !== 'start') {
    process.stderr.write(
      '--open-browser only applies to app-services start.\n',
    );
    usage(2);
  }
  if (options.openBrowser && !options.selectedServices.has('webgui-service')) {
    process.stderr.write(
      '--open-browser requires selecting --webgui or --all.\n',
    );
    usage(2);
  }
  if (options.yes && !options.dryRun && options.selectedServices.size === 0) {
    process.stderr.write('Select at least one service before using --yes.\n');
    usage(2);
  }

  return options;
}
