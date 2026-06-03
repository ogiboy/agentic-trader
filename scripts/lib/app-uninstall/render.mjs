export function renderHuman(payload) {
  process.stdout.write('Agentic Trader app:uninstall\n');
  process.stdout.write(`root: ${payload.root}\n`);
  process.stdout.write(`dry-run: ${payload.dry_run ? 'yes' : 'no'}\n`);
  process.stdout.write(
    `selected: ${
      payload.selected_scopes.length > 0
        ? payload.selected_scopes.join(', ')
        : 'none'
    }\n`,
  );
  for (const target of payload.targets) {
    const marker =
      target.status === 'removed'
        ? 'removed'
        : target.status === 'blocked'
          ? 'blocked'
          : target.status;
    process.stdout.write(`${marker} ${target.id}: ${target.relative_path}\n`);
    if (target.reason) {
      process.stdout.write(`  ${target.reason}\n`);
    }
  }
  if (payload.dry_run) {
    process.stdout.write(
      'Run pnpm run app:uninstall -- --artifacts --deps --yes to remove selected local artifacts/dependencies.\n',
    );
  }
}
