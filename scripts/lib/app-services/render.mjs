export function renderHuman(payload) {
  process.stdout.write(`Agentic Trader app:${payload.action}\n`);
  process.stdout.write(`dry-run: ${payload.dry_run ? 'yes' : 'no'}\n`);
  if (payload.selected_services.length > 0) {
    process.stdout.write(`selected: ${payload.selected_services.join(', ')}\n`);
  } else {
    process.stdout.write('selected: none\n');
  }
  for (const step of payload.steps) {
    const marker =
      step.status === 'passed'
        ? 'ok'
        : step.status === 'failed'
          ? 'fail'
          : step.status;
    process.stdout.write(`${marker} ${step.id}: ${step.label}\n`);
    if (step.status === 'deferred' && step.reason) {
      process.stdout.write(`  ${step.reason}\n`);
    }
    if (step.status === 'blocked' && step.reason) {
      process.stdout.write(`  ${step.reason}\n`);
    }
  }
  if (payload.dry_run) {
    process.stdout.write(
      `Run ${payload.next_commands[1]} to ${payload.action} the selected app-owned service scope.\n`,
    );
  }
}
