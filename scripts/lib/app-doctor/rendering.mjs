function yesNo(value) {
  return value ? 'yes' : 'no';
}

function payloadSummaryLines(result) {
  const payload = result.payload;
  if (!payload || typeof payload !== 'object') {
    return [];
  }
  if (result.id === 'setup-status') {
    return setupStatusLines(payload);
  }
  if (
    ['model-service', 'camofox-service', 'webgui-service'].includes(result.id)
  ) {
    return serviceStatusLines(payload);
  }
  if (result.id === 'provider-diagnostics') {
    return providerDiagnosticLines(payload);
  }
  if (result.id === 'v1-readiness') {
    return v1ReadinessLines(payload);
  }
  return [];
}

function setupStatusLines(payload) {
  const lines = [];
  if ('core_ready' in payload || 'optional_ready' in payload) {
    lines.push(
      `core_ready=${yesNo(payload.core_ready)} optional_ready=${yesNo(payload.optional_ready)}`,
    );
  }
  const tools = Array.isArray(payload.tools) ? payload.tools : [];
  const degradedTools = tools
    .filter(
      (tool) =>
        tool &&
        typeof tool === 'object' &&
        tool.status &&
        !['available', 'healthy', 'installed'].includes(String(tool.status)),
    )
    .slice(0, 4)
    .map((tool) => `${tool.tool_id || 'tool'}:${tool.status}`);
  if (degradedTools.length > 0) {
    lines.push(`degraded_tools=${degradedTools.join(', ')}`);
  }
  return lines;
}

function serviceStatusLines(payload) {
  const fields = [];
  if ('app_owned' in payload) {
    fields.push(`app_owned=${yesNo(payload.app_owned)}`);
  }
  if ('service_reachable' in payload) {
    fields.push(`service_reachable=${yesNo(payload.service_reachable)}`);
  }
  if (payload.message) {
    fields.push(`message=${String(payload.message)}`);
  }
  return fields.length > 0 ? [fields.join(' ')] : [];
}

function providerDiagnosticLines(payload) {
  const fields = [];
  if (payload.market_data && typeof payload.market_data === 'object') {
    fields.push(`market_provider=${payload.market_data.selected_provider ?? '-'}`);
  }
  if (Array.isArray(payload.warnings)) {
    fields.push(`warnings=${payload.warnings.length}`);
  }
  return fields.length > 0 ? [fields.join(' ')] : [];
}

function v1ReadinessLines(payload) {
  const paperOperations =
    payload.paper_operations && typeof payload.paper_operations === 'object'
      ? payload.paper_operations
      : null;
  const allowed =
    paperOperations && 'allowed' in paperOperations
      ? paperOperations.allowed
      : payload.ready;
  const fields = [`paper_operations_allowed=${yesNo(allowed)}`];
  const checks = Array.isArray(paperOperations?.checks)
    ? paperOperations.checks
    : [];
  const failedChecks = checks
    .filter((check) => check && typeof check === 'object' && !check.passed)
    .slice(0, 4)
    .map((check) => check.name || 'check');
  if (failedChecks.length > 0) {
    fields.push(`failed=${failedChecks.join(', ')}`);
  }
  return [fields.join(' ')];
}

export function renderHuman(payload) {
  process.stdout.write('Agentic Trader app:doctor\n');
  if (!payload.cli_path) {
    process.stdout.write(
      'local agentic-trader entrypoint was not found. Run make setup, set AGENTIC_TRADER_CLI, or set AGENTIC_TRADER_ALLOW_GLOBAL_CLI=1 intentionally.\n',
    );
    return;
  }
  for (const result of payload.steps) {
    process.stdout.write(
      `${result.status === 'passed' ? 'ok' : 'fail'} ${result.id}: ${result.label}\n`,
    );
    for (const line of payloadSummaryLines(result)) {
      process.stdout.write(`  ${line}\n`);
    }
  }
}
