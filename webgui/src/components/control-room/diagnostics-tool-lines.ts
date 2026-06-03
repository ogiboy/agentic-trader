import
  {
    diagnosticsCopy,
    localizedStatusText,
    sourceHealthSummaryLine,
    withOpenAiSuffix,
    yesNo,
  } from './diagnostics-formatting';
import type { ControlRoomCopy } from './labels';
import { asRecord, asString } from './payload';
import type { DashboardData } from './types';

function ownershipMode(dashboard: DashboardData, tool: string): string {
  const toolOwnership = asRecord(dashboard.toolOwnership);
  const decisions = asRecord(toolOwnership.decisions_by_tool);
  const decision = asRecord(decisions[tool]);
  return asString(decision.mode, 'undecided');
}

export function localToolLines(
  dashboard: DashboardData,
  copy?: ControlRoomCopy,
): string[] {
  const diagnostics = diagnosticsCopy(copy);
  const { labels, messages, values } = diagnostics;
  const modelService = asRecord(dashboard.modelService);
  const camofox = asRecord(dashboard.camofoxService);
  const doctor = asRecord(dashboard.doctor);
  const webGui = asRecord(dashboard.webGui);
  const research = asRecord(dashboard.research);
  const sourceHealth = asRecord(research.source_health_summary);
  const provider = asString(doctor.provider, 'ollama');
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
    `${labels.modelServiceUrl}: ${withOpenAiSuffix(
      modelService.base_url ?? modelService.configured_base_url,
    )}`,
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
    `${labels.camofoxUrl}: ${asString(camofox.base_url)}`,
    `${labels.webGui}: ${localizedStatusText(webGui.message, copy)}`,
    `${labels.webGuiOwned}: ${yesNo(webGui.app_owned, copy)}`,
    `${labels.webGuiUrl}: ${asString(webGui.url)}`,
    `${labels.research}: ${asString(research.status)} (${asString(research.backend)})`,
    `${labels.researchSources}: ${sourceHealthSummaryLine(sourceHealth, copy)}`,
  ];
}

export function localToolActionLines(
  dashboard: DashboardData,
  copy?: ControlRoomCopy,
): string[] {
  const { actions } = diagnosticsCopy(copy);
  const modelService = asRecord(dashboard.modelService);
  const camofox = asRecord(dashboard.camofoxService);
  const doctor = asRecord(dashboard.doctor);
  const provider = asString(doctor.provider, 'ollama');
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
