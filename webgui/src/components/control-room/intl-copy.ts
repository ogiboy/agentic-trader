import { useMemo } from 'react';
import { useTranslations } from 'next-intl';

import type { ControlRoomDiagnosticsCopy } from './copy/diagnostics-types';
import type { ControlRoomCopy } from './copy/types';

export type ControlRoomCurrentCycleCopy = {
  cycleCount: string;
  currentStage: string;
  currentSymbol: string;
  lastOutcome: string;
  mode: string;
  runtime: string;
  stageStatus: string;
  status: string;
  waitingOutcome: string;
};

function displayScalar(value: unknown, fallback: string): string {
  if (
    typeof value === 'string' ||
    typeof value === 'number' ||
    typeof value === 'boolean'
  ) {
    return String(value);
  }
  return fallback;
}

export function useControlRoomCurrentCycleCopy(): ControlRoomCurrentCycleCopy {
  const t = useTranslations('controlRoom.currentCycle');

  return useMemo(
    () => ({
      cycleCount: t('cycleCount'),
      currentStage: t('currentStage'),
      currentSymbol: t('currentSymbol'),
      lastOutcome: t('lastOutcome'),
      mode: t('mode'),
      runtime: t('runtime'),
      stageStatus: t('stageStatus'),
      status: t('status'),
      waitingOutcome: t('waitingOutcome'),
    }),
    [t],
  );
}

export function useControlRoomDiagnosticsCopy(): ControlRoomDiagnosticsCopy {
  const t = useTranslations('controlRoom.diagnostics');

  return useMemo(
    () => ({
      actions: {
        camofoxAccessKeyMissing: t('actions.camofoxAccessKeyMissing'),
        camofoxAppManagedNotRunning: t('actions.camofoxAppManagedNotRunning'),
        camofoxHostManagedUnreachable: t(
          'actions.camofoxHostManagedUnreachable',
        ),
        camofoxOwnershipUndecided: t('actions.camofoxOwnershipUndecided'),
        ollamaAppManagedNotRunning: t('actions.ollamaAppManagedNotRunning'),
        ollamaHostManagedUnreachable: t(
          'actions.ollamaHostManagedUnreachable',
        ),
        ollamaModelMissing: (model: unknown) =>
          t('actions.ollamaModelMissing', {
            model: displayScalar(model, 'the configured model'),
          }),
        ollamaOwnershipUndecided: t('actions.ollamaOwnershipUndecided'),
      },
      labels: {
        alpacaKey: t('labels.alpacaKey'),
        backend: t('labels.backend'),
        baseUrl: t('labels.baseUrl'),
        brokerBackend: t('labels.brokerBackend'),
        brokerHealth: t('labels.brokerHealth'),
        brokerState: t('labels.brokerState'),
        camofox: t('labels.camofox'),
        camofoxAccessKey: t('labels.camofoxAccessKey'),
        camofoxBlocker: t('labels.camofoxBlocker'),
        camofoxOwned: t('labels.camofoxOwned'),
        camofoxOwnership: t('labels.camofoxOwnership'),
        camofoxReachable: t('labels.camofoxReachable'),
        camofoxService: t('labels.camofoxService'),
        camofoxUrl: t('labels.camofoxUrl'),
        canRunLocalPaperCycle: t('labels.canRunLocalPaperCycle'),
        canUseAlpacaPaper: t('labels.canUseAlpacaPaper'),
        executionMode: t('labels.executionMode'),
        externalPaperModeActive: t('labels.externalPaperModeActive'),
        finnhubKey: t('labels.finnhubKey'),
        firecrawlOwnership: t('labels.firecrawlOwnership'),
        firecrawlRuntime: t('labels.firecrawlRuntime'),
        fmpKey: t('labels.fmpKey'),
        freshSources: t('labels.freshSources'),
        killSwitch: t('labels.killSwitch'),
        llmReachable: t('labels.llmReachable'),
        llmRuntime: t('labels.llmRuntime'),
        marketProvider: t('labels.marketProvider'),
        marketRole: t('labels.marketRole'),
        marketSession: t('labels.marketSession'),
        model: t('labels.model'),
        modelAdapter: t('labels.modelAdapter'),
        modelAvailable: t('labels.modelAvailable'),
        modelService: t('labels.modelService'),
        modelServiceOwned: t('labels.modelServiceOwned'),
        modelServiceReachable: t('labels.modelServiceReachable'),
        modelServiceUrl: t('labels.modelServiceUrl'),
        newsMode: t('labels.newsMode'),
        ollamaOwnership: t('labels.ollamaOwnership'),
        ollamaReachable: t('labels.ollamaReachable'),
        provider: t('labels.provider'),
        research: t('labels.research'),
        researchControl: t('labels.researchControl'),
        researchDigestReplay: t('labels.researchDigestReplay'),
        researchSources: t('labels.researchSources'),
        researchTrigger: t('labels.researchTrigger'),
        sourceMissing: t('labels.sourceMissing'),
        sourceUnknown: t('labels.sourceUnknown'),
        webGui: t('labels.webGui'),
        webGuiOwned: t('labels.webGuiOwned'),
        webGuiService: t('labels.webGuiService'),
        webGuiUrl: t('labels.webGuiUrl'),
        whyAlpacaPaperBlocked: t('labels.whyAlpacaPaperBlocked'),
        whyPaperCycleBlocked: t('labels.whyPaperCycleBlocked'),
      },
      messages: {
        appOwnedRuntime: t('messages.appOwnedRuntime'),
        camofoxAccessKeyMissing: t('messages.camofoxAccessKeyMissing'),
        firecrawlRuntime: t('messages.firecrawlRuntime'),
        internalFirstRuntime: t('messages.internalFirstRuntime'),
        noProviderWarnings: t('messages.noProviderWarnings'),
        status: {
          alpacaPaperReady: t('messages.status.alpacaPaperReady'),
          camofoxReachable: t('messages.status.camofoxReachable'),
          modelServiceHostDefault: t(
            'messages.status.modelServiceHostDefault',
          ),
          noRuntimeState: t('messages.status.noRuntimeState'),
          webGuiStateStale: t('messages.status.webGuiStateStale'),
        },
      },
      values: {
        active: t('values.active'),
        available: t('values.available'),
        clear: t('values.clear'),
        configured: t('values.configured'),
        disabledByOwnership: t('values.disabledByOwnership'),
        enabled: t('values.enabled'),
        inactive: t('values.inactive'),
        missing: t('values.missing'),
        no: t('values.no'),
        requested: t('values.requested'),
        yes: t('values.yes'),
      },
    }),
    [t],
  );
}

export function usePortfolioContextCopy(): ControlRoomCopy['portfolio']['context'] {
  const t = useTranslations('controlRoom.portfolio.context');

  return useMemo(
    () => ({
      positionPlanCoverage: t('positionPlanCoverage'),
      positionPlanEmpty: t('positionPlanEmpty'),
      positionPlanExitPlans: t('positionPlanExitPlans'),
      positionPlanMissingPlans: t('positionPlanMissingPlans'),
      positionPlanOpenPositions: t('positionPlanOpenPositions'),
      positionPlanUnavailable: t('positionPlanUnavailable'),
      unavailable: t('unavailable'),
      unknownError: t('unknownError'),
    }),
    [t],
  );
}

export function useProposalContextCopy(): ControlRoomCopy['proposals']['context'] {
  const t = useTranslations('controlRoom.proposals.context');

  return useMemo(
    () => ({
      brokerStateBlocked: t('brokerStateBlocked'),
      confidence: t('confidence'),
      empty: t('empty'),
      killSwitchActive: t('killSwitchActive'),
      liveBackendBlocked: t('liveBackendBlocked'),
      quantity: t('quantity'),
      source: t('source'),
      unavailable: t('unavailable'),
      unknownError: t('unknownError'),
    }),
    [t],
  );
}

export function useReviewContextCopy(): ControlRoomCopy['review']['context'] {
  const t = useTranslations('controlRoom.review.context');

  return useMemo(
    () => ({
      canonicalCompleteness: t('canonicalCompleteness'),
      canonicalDisclosures: t('canonicalDisclosures'),
      canonicalEmpty: t('canonicalEmpty'),
      canonicalFundamentalSource: t('canonicalFundamentalSource'),
      canonicalMacroSource: t('canonicalMacroSource'),
      canonicalMarketSource: t('canonicalMarketSource'),
      canonicalMissingSections: t('canonicalMissingSections'),
      canonicalNewsEvents: t('canonicalNewsEvents'),
      canonicalSource: t('canonicalSource'),
      canonicalSummary: t('canonicalSummary'),
      marketAnomalies: t('marketAnomalies'),
      marketCoverage: t('marketCoverage'),
      marketDrawdown: t('marketDrawdown'),
      marketEmpty: t('marketEmpty'),
      marketHorizon: t('marketHorizon'),
      marketInterval: t('marketInterval'),
      marketLookbackInterval: t('marketLookbackInterval'),
      marketQuality: t('marketQuality'),
      marketReturn: t('marketReturn'),
      marketSummary: t('marketSummary'),
      marketWindow: t('marketWindow'),
      tradeConsensus: t('tradeConsensus'),
      tradeEmpty: t('tradeEmpty'),
      tradeExecutionAdapter: t('tradeExecutionAdapter'),
      tradeExecutionBackend: t('tradeExecutionBackend'),
      tradeExecutionOutcome: t('tradeExecutionOutcome'),
      tradeExecutionRationale: t('tradeExecutionRationale'),
      tradeId: t('tradeId'),
      tradeManagerRationale: t('tradeManagerRationale'),
      tradeRejectionReason: t('tradeRejectionReason'),
      tradeReviewSummary: t('tradeReviewSummary'),
      tradeRoutedModels: t('tradeRoutedModels'),
      tradeRunId: t('tradeRunId'),
      unavailable: t('unavailable'),
      unknownError: t('unknownError'),
    }),
    [t],
  );
}
