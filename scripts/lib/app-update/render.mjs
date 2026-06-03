import { ROOT_DIR } from '../app-lifecycle.mjs';

export function renderHuman(payload) {
  process.stdout.write('Agentic Trader app:update\n');
  process.stdout.write(`dry-run: ${payload.dry_run ? 'yes' : 'no'}\n`);
  process.stdout.write(
    `selected: ${
      payload.selected_scopes.length > 0
        ? payload.selected_scopes.join(', ')
        : 'none'
    }\n`,
  );
  for (const step of payload.steps) {
    const marker =
      step.status === 'passed'
        ? 'ok'
        : step.status === 'failed'
          ? 'fail'
          : step.status;
    const cwdNote = step.cwd === ROOT_DIR ? '' : ` (${step.cwd})`;
    process.stdout.write(`${marker} ${step.id}${cwdNote}: ${step.label}\n`);
    if (step.reason) {
      process.stdout.write(`  ${step.reason}\n`);
    }
  }
  if (payload.dry_run) {
    process.stdout.write(
      'Run pnpm run app:update -- --core --build --status --yes to execute a scoped update lane.\n',
    );
  }
}
