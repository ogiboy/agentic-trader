export function renderHuman(payload) {
  process.stdout.write('Agentic Trader app:setup\n');
  process.stdout.write(`mode: ${payload.mode}\n`);
  process.stdout.write(`dry-run: ${payload.dry_run ? 'yes' : 'no'}\n`);
  for (const step of payload.steps) {
    const marker =
      step.status === 'passed'
        ? 'ok'
        : step.status === 'failed'
          ? 'fail'
          : step.status;
    process.stdout.write(`${marker} ${step.id}: ${step.label}\n`);
    if (step.reason) {
      process.stdout.write(`  ${step.reason}\n`);
    }
  }
  if (payload.dry_run) {
    process.stdout.write(
      'Run pnpm run app:setup -- --core --yes to execute only core dependency repair.\n',
    );
  }
}
