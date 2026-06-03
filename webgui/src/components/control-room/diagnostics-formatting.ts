import { getControlRoomCopy, type ControlRoomCopy } from './labels';
import { asRecord, asRecordArray, asString } from './payload';
import type {
  DashboardData,
  DashboardRecord,
  KeyValueItems,
} from './types';

export function diagnosticsCopy(
  copy?: ControlRoomCopy,
): ControlRoomCopy['diagnostics'] {
  return (copy ?? getControlRoomCopy('en')).diagnostics;
}

export function yesNo(value: unknown, copy?: ControlRoomCopy): string {
  const values = diagnosticsCopy(copy).values;
  return value ? values.yes : values.no;
}

export function localizedStatusText(
  value: unknown,
  copy?: ControlRoomCopy,
): string {
  if (typeof value !== 'string' || value === '') {
    return '-';
  }
  const status = diagnosticsCopy(copy).messages.status;
  if (value === 'Alpaca paper adapter is configured for paper trading.') {
    return status.alpacaPaperReady;
  }
  if (value === 'Camofox server is reachable; browser launches on demand.') {
    return status.camofoxReachable;
  }
  if (
    value ===
    'Ollama is reachable. This is a host/default Ollama service; model-service stop will not kill it.'
  ) {
    return status.modelServiceHostDefault;
  }
  if (value === 'No runtime state has been recorded yet.') {
    return status.noRuntimeState;
  }
  if (
    value ===
    'Recorded Web GUI state is stale or process ownership could not be verified.'
  ) {
    return status.webGuiStateStale;
  }
  return value;
}

export function sourceHealthSummaryLine(
  summary: unknown,
  copy?: ControlRoomCopy,
): string {
  const sourceSummary = asRecord(summary);
  if (!Object.keys(sourceSummary).length) {
    return '-';
  }
  const { labels } = diagnosticsCopy(copy);
  const fresh = formatSourceHealthCount(sourceSummary.fresh);
  const missing = formatSourceHealthCount(sourceSummary.missing);
  const unknown = formatSourceHealthCount(sourceSummary.unknown);
  return `${labels.freshSources} ${fresh} / ${labels.sourceMissing} ${missing} / ${labels.sourceUnknown} ${unknown}`;
}

export function formatSourceHealthCount(value: unknown): string {
  if (value === null || value === undefined) {
    return '0';
  }
  if (
    typeof value === 'string' ||
    typeof value === 'number' ||
    typeof value === 'boolean'
  ) {
    return String(value);
  }
  return '0';
}

export function failedCheckNames(
  section: DashboardRecord | undefined,
): string {
  const failed = asRecordArray(section?.checks)
    .filter(
      (item) => item.blocking !== false && !item.passed,
    )
    .map((item) => asString(item.name))
    .slice(0, 3);
  return failed.length ? failed.join(', ') : '-';
}

export function readinessLines(
  dashboard: DashboardData,
  copy?: ControlRoomCopy,
): string[] {
  const diagnostics = diagnosticsCopy(copy);
  const { labels } = diagnostics;
  const readiness = asRecord(dashboard.v1Readiness);
  const broker = asRecord(dashboard.broker);
  const paper = asRecord(readiness.paper_operations);
  const alpaca = asRecord(readiness.alpaca_paper);
  const healthcheck = asRecord(broker.healthcheck);
  return [
    `${labels.canRunLocalPaperCycle}: ${yesNo(paper.allowed, copy)}`,
    `${labels.whyPaperCycleBlocked}: ${failedCheckNames(paper)}`,
    `${labels.canUseAlpacaPaper}: ${yesNo(alpaca.ready, copy)}`,
    `${labels.whyAlpacaPaperBlocked}: ${failedCheckNames(alpaca)}`,
    `${labels.backend}: ${asString(broker.backend)}`,
    `${labels.externalPaperModeActive}: ${yesNo(broker.external_paper, copy)}`,
    `${labels.killSwitch}: ${
      broker.kill_switch_active
        ? diagnostics.values.active
        : diagnostics.values.inactive
    }`,
    `${labels.brokerHealth}: ${asString(healthcheck.message, asString(broker.message))}`,
  ];
}

export function providerWarningLines(
  dashboard: DashboardData,
  copy?: ControlRoomCopy,
): string[] {
  const diagnostics = diagnosticsCopy(copy);
  const { labels, messages, values } = diagnostics;
  const providerDiagnostics = asRecord(dashboard.providerDiagnostics);
  const market = asRecord(providerDiagnostics.market_data);
  const keys = asRecord(providerDiagnostics.configured_keys);
  const news = asRecord(providerDiagnostics.news);
  const warnings = Array.isArray(providerDiagnostics.warnings)
    ? providerDiagnostics.warnings
    : [];
  const keyState = (configured: unknown) =>
    configured ? values.configured : values.missing;
  return [
    `${labels.marketProvider}: ${asString(market.selected_provider)}`,
    `${labels.marketRole}: ${asString(market.selected_role)}`,
    `${labels.newsMode}: ${asString(news.mode)}`,
    `${labels.finnhubKey}: ${keyState(keys.finnhub)}`,
    `${labels.fmpKey}: ${keyState(keys.fmp)}`,
    `${labels.alpacaKey}: ${keyState(keys.alpaca)}`,
    ...(warnings.length
      ? warnings.slice(0, 3).map((warning) => asString(warning))
      : [messages.noProviderWarnings]),
  ];
}

export function withOpenAiSuffix(baseUrl: unknown): string {
  if (typeof baseUrl !== 'string' || !baseUrl.trim()) {
    return '-';
  }
  const trimmed = baseUrl.replace(/\/$/, '');
  return trimmed.endsWith('/v1') ? trimmed : `${trimmed}/v1`;
}

function effectiveModelBaseUrl(dashboard: DashboardData | null): string {
  const modelService = asRecord(dashboard?.modelService);
  const doctor = asRecord(dashboard?.doctor);
  if (modelService.app_owned && modelService.base_url) {
    return withOpenAiSuffix(modelService.base_url);
  }
  if (doctor.base_url) {
    return withOpenAiSuffix(doctor.base_url);
  }
  return '-';
}

function effectiveBoolean(
  appOwnedValue: unknown,
  fallbackValue: unknown,
  copy?: ControlRoomCopy,
): string {
  return yesNo(appOwnedValue ?? fallbackValue, copy);
}

export function systemStatusItems(
  dashboard: DashboardData | null,
  copy?: ControlRoomCopy,
): KeyValueItems {
  const diagnostics = diagnosticsCopy(copy);
  const { labels, values } = diagnostics;
  const modelService = asRecord(dashboard?.modelService);
  const doctor = asRecord(dashboard?.doctor);
  const camofoxService = asRecord(dashboard?.camofoxService);
  const webGui = asRecord(dashboard?.webGui);
  const research = asRecord(dashboard?.research);
  const cycleControl = asRecord(research.cycleControl);
  const latestDigestReplay = asRecord(research.latestDigestReplay);
  const broker = asRecord(dashboard?.broker);
  const calendar = asRecord(dashboard?.calendar);
  const session = asRecord(calendar.session);
  const provider = asString(doctor.provider, 'ollama');
  const reachabilityLabel =
    provider === 'ollama' ? labels.ollamaReachable : labels.llmReachable;
  return [
    [labels.provider, provider],
    [
      labels.model,
      asString(doctor.model, asString(modelService.configured_model)),
    ],
    [labels.baseUrl, effectiveModelBaseUrl(dashboard)],
    [
      reachabilityLabel,
      effectiveBoolean(
        modelService.app_owned ? modelService.service_reachable : undefined,
        doctor.llm_reachable ?? doctor.ollama_reachable,
        copy,
      ),
    ],
    [
      labels.modelAvailable,
      effectiveBoolean(
        modelService.app_owned ? modelService.model_available : undefined,
        doctor.model_available,
        copy,
      ),
    ],
    [labels.modelService, localizedStatusText(modelService.message, copy)],
    [
      labels.camofoxService,
      localizedStatusText(camofoxService.message, copy),
    ],
    [
      labels.webGuiService,
      localizedStatusText(webGui.message, copy),
    ],
    [labels.research, asString(research.status)],
    [labels.researchControl, asString(cycleControl.status)],
    [
      labels.researchTrigger,
      cycleControl.trigger_now_requested
        ? values.requested
        : values.clear,
    ],
    [
      labels.researchDigestReplay,
      latestDigestReplay.available
        ? values.available
        : '-',
    ],
    [
      labels.researchSources,
      sourceHealthSummaryLine(
        asRecord(research.source_health_summary),
        copy,
      ),
    ],
    [labels.brokerBackend, asString(broker.backend)],
    [labels.brokerState, asString(broker.state)],
    [labels.executionMode, asString(broker.execution_mode)],
    [labels.marketSession, asString(session.session_state)],
  ];
}
