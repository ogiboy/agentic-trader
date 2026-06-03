export function renderHuman(payload) {
  process.stdout.write('Agentic Trader app:up\n');
  process.stdout.write(`dry-run: ${payload.dry_run ? 'yes' : 'no'}\n`);
  process.stdout.write(
    `selected: ${
      payload.selected_scopes.length > 0
        ? payload.selected_scopes.join(', ')
        : 'none'
    }\n`,
  );
  process.stdout.write(
    `ownership: ${payload.ownership_decisions
      .map((decision) => `${decision.tool}=${decision.mode}`)
      .join(', ')}\n`,
  );
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
  process.stdout.write('summary:\n');
  for (const key of ['done', 'not_done', 'deferred']) {
    const items = payload.summary?.[key] ?? [];
    process.stdout.write(`  ${key}: ${items.length}\n`);
    for (const item of items) {
      process.stdout.write(`    - ${item.id}: ${item.reason || item.label}\n`);
    }
  }
  if (payload.dry_run) {
    process.stdout.write(
      'Run pnpm run app:up -- --all --yes for the safe first-run setup path.\n',
    );
  }
}
