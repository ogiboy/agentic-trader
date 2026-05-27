/* eslint-disable @typescript-eslint/no-explicit-any -- dashboard diagnostics payloads are schema-loose JSON today */
import type { DashboardData, KeyValueItems } from '../control-room.helpers';
import { getControlRoomCopy, type ControlRoomCopy } from './labels';

function diagnosticsCopy(
  copy?: ControlRoomCopy,
): ControlRoomCopy['diagnostics'] {
  return (copy ?? getControlRoomCopy('en')).diagnostics;
}

function yesNo(value: unknown, copy?: ControlRoomCopy): string {
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
  summary: Record<string, unknown> | undefined,
  copy?: ControlRoomCopy,
): string {
  if (!summary) {
    return '-';
  }
  const { labels } = diagnosticsCopy(copy);
  const fresh = formatSourceHealthCount(summary.fresh);
  const missing = formatSourceHealthCount(summary.missing);
  const unknown = formatSourceHealthCount(summary.unknown);
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
  section: Record<string, any> | undefined,
): string {
  const failed = (section?.checks || [])
    .filter(
      (item: Record<string, any>) => item.blocking !== false && !item.passed,
    )
    .map((item: Record<string, any>) => item.name)
    .slice(0, 3);
  return failed.length ? failed.join(', ') : '-';
}

export function readinessLines(
  dashboard: DashboardData,
  copy?: ControlRoomCopy,
): string[] {
  const diagnostics = diagnosticsCopy(copy);
  const { labels } = diagnostics;
  const readiness = dashboard.v1Readiness || {};
  const broker = dashboard.broker || {};
  const paper = readiness.paper_operations || {};
  const alpaca = readiness.alpaca_paper || {};
  return [
    `${labels.canRunLocalPaperCycle}: ${yesNo(paper.allowed, copy)}`,
    `${labels.whyPaperCycleBlocked}: ${failedCheckNames(paper)}`,
    `${labels.canUseAlpacaPaper}: ${yesNo(alpaca.ready, copy)}`,
    `${labels.whyAlpacaPaperBlocked}: ${failedCheckNames(alpaca)}`,
    `${labels.backend}: ${broker.backend ?? '-'}`,
    `${labels.externalPaperModeActive}: ${yesNo(broker.external_paper, copy)}`,
    `${labels.killSwitch}: ${
      broker.kill_switch_active
        ? diagnostics.values.active
        : diagnostics.values.inactive
    }`,
    `${labels.brokerHealth}: ${broker.healthcheck?.message ?? broker.message ?? '-'}`,
  ];
}

export function providerWarningLines(
  dashboard: DashboardData,
  copy?: ControlRoomCopy,
): string[] {
  const diagnostics = diagnosticsCopy(copy);
  const { labels, messages, values } = diagnostics;
  const providerDiagnostics = dashboard.providerDiagnostics || {};
  const market = providerDiagnostics.market_data || {};
  const keys = providerDiagnostics.configured_keys || {};
  const warnings = Array.isArray(providerDiagnostics.warnings)
    ? providerDiagnostics.warnings
    : [];
  const keyState = (configured: unknown) =>
    configured ? values.configured : values.missing;
  return [
    `${labels.marketProvider}: ${market.selected_provider ?? '-'}`,
    `${labels.marketRole}: ${market.selected_role ?? '-'}`,
    `${labels.newsMode}: ${providerDiagnostics.news?.mode ?? '-'}`,
    `${labels.finnhubKey}: ${keyState(keys.finnhub)}`,
    `${labels.fmpKey}: ${keyState(keys.fmp)}`,
    `${labels.alpacaKey}: ${keyState(keys.alpaca)}`,
    ...(warnings.length ? warnings.slice(0, 3) : [messages.noProviderWarnings]),
  ];
}

function ownershipMode(dashboard: DashboardData, tool: string): string {
  return (
    dashboard.toolOwnership?.decisions_by_tool?.[tool]?.mode ?? 'undecided'
  );
}

function withOpenAiSuffix(baseUrl: unknown): string {
  if (typeof baseUrl !== 'string' || !baseUrl.trim()) {
    return '-';
  }
  const trimmed = baseUrl.replace(/\/$/, '');
  return trimmed.endsWith('/v1') ? trimmed : `${trimmed}/v1`;
}

function effectiveModelBaseUrl(dashboard: DashboardData | null): string {
  const modelService = dashboard?.modelService || {};
  if (modelService.app_owned && modelService.base_url) {
    return withOpenAiSuffix(modelService.base_url);
  }
  if (dashboard?.doctor?.base_url) {
    return withOpenAiSuffix(dashboard.doctor.base_url);
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
  const modelService = dashboard?.modelService || {};
  const provider = dashboard?.doctor?.provider ?? 'ollama';
  const reachabilityLabel =
    provider === 'ollama' ? labels.ollamaReachable : labels.llmReachable;
  return [
    [labels.provider, provider],
    [
      labels.model,
      dashboard?.doctor?.model ?? modelService.configured_model ?? '-',
    ],
    [labels.baseUrl, effectiveModelBaseUrl(dashboard)],
    [
      reachabilityLabel,
      effectiveBoolean(
        modelService.app_owned ? modelService.service_reachable : undefined,
        dashboard?.doctor?.llm_reachable ?? dashboard?.doctor?.ollama_reachable,
        copy,
      ),
    ],
    [
      labels.modelAvailable,
      effectiveBoolean(
        modelService.app_owned ? modelService.model_available : undefined,
        dashboard?.doctor?.model_available,
        copy,
      ),
    ],
    [labels.modelService, localizedStatusText(modelService.message, copy)],
    [
      labels.camofoxService,
      localizedStatusText(dashboard?.camofoxService?.message, copy),
    ],
    [
      labels.webGuiService,
      localizedStatusText(dashboard?.webGui?.message, copy),
    ],
    [labels.research, dashboard?.research?.status ?? '-'],
    [labels.researchControl, dashboard?.research?.cycleControl?.status ?? '-'],
    [
      labels.researchTrigger,
      dashboard?.research?.cycleControl?.trigger_now_requested
        ? values.requested
        : values.clear,
    ],
    [
      labels.researchDigestReplay,
      dashboard?.research?.latestDigestReplay?.available
        ? values.available
        : '-',
    ],
    [
      labels.researchSources,
      sourceHealthSummaryLine(dashboard?.research?.source_health_summary, copy),
    ],
    [labels.brokerBackend, dashboard?.broker?.backend ?? '-'],
    [labels.brokerState, dashboard?.broker?.state ?? '-'],
    [labels.executionMode, dashboard?.broker?.execution_mode ?? '-'],
    [labels.marketSession, dashboard?.calendar?.session?.session_state ?? '-'],
  ];
}

export function localToolLines(
  dashboard: DashboardData,
  copy?: ControlRoomCopy,
): string[] {
  const diagnostics = diagnosticsCopy(copy);
  const { labels, messages, values } = diagnostics;
  const modelService = dashboard.modelService || {};
  const camofox = dashboard.camofoxService || {};
  const provider = dashboard.doctor?.provider ?? 'ollama';
  const firecrawlMode = ownershipMode(dashboard, 'firecrawl');
  let camofoxBlocker = `${labels.camofoxAccessKey}: -`;
  if (camofox.access_key_configured === false) {
    camofoxBlocker = `${labels.camofoxBlocker}: ${messages.camofoxAccessKeyMissing}`;
  } else if (camofox.access_key_configured) {
    camofoxBlocker = `${labels.camofoxAccessKey}: ${values.configured}`;
  }
  return [
    `${labels.modelAdapter}: ${provider}`,
    `${labels.llmRuntime}: ${messages.internalFirstRuntime}${
      modelService.app_owned ? ` ${messages.appOwnedRuntime}` : ''
    }`,
    `${labels.modelService}: ${localizedStatusText(modelService.message, copy)}`,
    `${labels.ollamaOwnership}: ${ownershipMode(dashboard, 'ollama')}`,
    `${labels.modelServiceOwned}: ${yesNo(modelService.app_owned, copy)}`,
    `${labels.modelServiceReachable}: ${yesNo(
      modelService.service_reachable,
      copy,
    )}`,
    `${labels.modelAvailable}: ${yesNo(modelService.model_available, copy)}`,
    `${labels.modelServiceUrl}: ${withOpenAiSuffix(modelService.base_url ?? modelService.configured_base_url)}`,
    `${labels.firecrawlOwnership}: ${firecrawlMode}`,
    `${labels.firecrawlRuntime}: ${messages.firecrawlRuntime} ${
      firecrawlMode === 'host-owned'
        ? values.enabled
        : values.disabledByOwnership
    }`,
    `${labels.camofox}: ${localizedStatusText(camofox.message, copy)}`,
    `${labels.camofoxOwnership}: ${ownershipMode(dashboard, 'camofox')}`,
    `${labels.camofoxOwned}: ${yesNo(camofox.app_owned, copy)}`,
    `${labels.camofoxReachable}: ${yesNo(camofox.service_reachable, copy)}`,
    camofoxBlocker,
    `${labels.camofoxUrl}: ${camofox.base_url ?? '-'}`,
    `${labels.webGui}: ${localizedStatusText(dashboard.webGui?.message, copy)}`,
    `${labels.webGuiOwned}: ${yesNo(dashboard.webGui?.app_owned, copy)}`,
    `${labels.webGuiUrl}: ${dashboard.webGui?.url ?? '-'}`,
    `${labels.research}: ${dashboard.research?.status ?? '-'} (${dashboard.research?.backend ?? '-'})`,
    `${labels.researchSources}: ${sourceHealthSummaryLine(dashboard.research?.source_health_summary, copy)}`,
  ];
}

export function localToolActionLines(
  dashboard: DashboardData,
  copy?: ControlRoomCopy,
): string[] {
  const { actions } = diagnosticsCopy(copy);
  const modelService = dashboard.modelService || {};
  const camofox = dashboard.camofoxService || {};
  const provider = dashboard.doctor?.provider ?? 'ollama';
  const ollamaMode = ownershipMode(dashboard, 'ollama');
  const camofoxMode = ownershipMode(dashboard, 'camofox');
  const lines: string[] = [];

  if (provider === 'ollama' && !modelService.service_reachable) {
    if (ollamaMode === 'app-owned') {
      lines.push(actions.ollamaAppManagedNotRunning);
    } else if (ollamaMode === 'host-owned') {
      lines.push(actions.ollamaHostManagedUnreachable);
    } else {
      lines.push(actions.ollamaOwnershipUndecided);
    }
  } else if (provider === 'ollama' && !modelService.model_available) {
    lines.push(actions.ollamaModelMissing(modelService.configured_model));
  }

  if (camofoxMode === 'app-owned' && !camofox.service_reachable) {
    lines.push(actions.camofoxAppManagedNotRunning);
  } else if (camofoxMode === 'host-owned' && !camofox.service_reachable) {
    lines.push(actions.camofoxHostManagedUnreachable);
  } else if (camofoxMode === 'undecided') {
    lines.push(actions.camofoxOwnershipUndecided);
  }

  if (camofox.access_key_configured === false) {
    lines.push(actions.camofoxAccessKeyMissing);
  }

  return lines;
}
