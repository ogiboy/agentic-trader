import type { TabId } from '../../control-room.helpers';
import type { ControlRoomDiagnosticsCopy } from './diagnostics-types';
import {
  WEBGUI_LOCALE_OPTIONS,
  type WebguiLocale,
} from '@/i18n/locales';

export type ControlRoomLocale = WebguiLocale;
export {
  WEBGUI_LOCALE_STORAGE_KEY as CONTROL_ROOM_LOCALE_STORAGE_KEY,
} from '@/i18n/locales';

export type ControlRoomCopy = {
  common: {
    no: string;
    off: string;
    on: string;
    yes: string;
    working: string;
  };
  diagnostics: ControlRoomDiagnosticsCopy;
  auth: {
    body: string;
    eyebrow: string;
    title: string;
    tokenLabel: string;
    unlock: string;
    unlocking: string;
  };
  hero: {
    alt: string;
    copy: string;
    eyebrow: string;
    sessionUnknown: string;
    title: string;
  };
  feedback: {
    dashboardRefreshed: string;
    instructionPreviewReady: string;
    operatorReplyReceived: string;
    preferencesUpdated: string;
  };
  chat: {
    empty: string;
    panels: {
      decisionWorkflowContext: string;
      operatorChat: string;
    };
    personas: Record<string, string>;
    placeholder: string;
    role: string;
    send: string;
    userLabel: string;
    workflow: {
      completedDetail: string;
      currentStage: string;
      lastCompleted: string;
      memoryRoles: string;
      stageDetail: string;
      stageStatus: string;
      toolRoles: string;
    };
  };
  currentCycle: {
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
  overview: {
    emptyStageEvents: string;
    panels: {
      currentCycle: string;
      decisionWorkflow: string;
      localTools: string;
      providerWarnings: string;
      readinessGates: string;
      system: string;
    };
    tools: {
      appTools: string;
      camofox: string;
      hostFallback: string;
      ollama: string;
    };
  };
  memory: {
    emptyRetrieval: string;
    emptySimilar: string;
    labels: {
      memoryExplorer: string;
      noRetrievalContext: string;
      retrievalInspection: string;
      sample: string;
      why: string;
    };
    panels: {
      similarPastRuns: string;
      whyContextWasUsed: string;
    };
  };
  portfolio: {
    emptyTradeJournal: string;
    fields: {
      behavior: string;
      basisPoints: string;
      cash: string;
      currencies: string;
      currency: string;
      deskFees: string;
      drawdown: string;
      equity: string;
      exchanges: string;
      generatedAt: string;
      grossExposure: string;
      largestPosition: string;
      markSource: string;
      markStatus: string;
      markedAt: string;
      marketValue: string;
      openPositions: string;
      paperMark: string;
      realizedPnl: string;
      regions: string;
      rejectionEvidence: string;
      risk: string;
      sectors: string;
      slippage: string;
      strictness: string;
      style: string;
      tone: string;
      unrealizedPnl: string;
      warnings: string;
    };
    noWarnings: string;
    panels: {
      deskAccountingNotes: string;
      exitPlanCoverage: string;
      portfolio: string;
      preferences: string;
      riskReport: string;
      tradeJournal: string;
    };
    unavailable: {
      portfolio: string;
      riskReport: string;
      tradeJournal: string;
    };
  };
  proposals: {
    actions: Record<
      'approve' | 'reject' | 'reconcile' | 'refresh',
      {
        label: string;
        title: string;
      }
    >;
    fields: {
      backend: string;
      externalPaper: string;
      killSwitch: string;
      liveRequested: string;
      message: string;
      state: string;
    };
    notePlaceholder: string;
    panels: {
      deskSafety: string;
      proposalDesk: string;
    };
    stopTake: (stop: string, take: string) => string;
  };
  review: {
    emptyPersistedRuns: string;
    fields: {
      approved: string;
      consensus: string;
      coordinatorFocus: string;
      created: string;
      reviewSummary: string;
      runId: string;
      symbol: string;
    };
    panels: {
      canonicalAnalysis: string;
      latestReview: string;
      marketContextPack: string;
      tradeContext: string;
    };
    unavailable: {
      latestReview: string;
    };
  };
  runtime: {
    empty: {
      events: string;
      stderr: string;
      stdout: string;
    };
    fields: {
      currentSymbol: string;
      cycleCount: string;
      liveProcess: string;
      pid: string;
      runtime: string;
      status: string;
      stopRequested: string;
      updated: string;
    };
    panels: {
      events: string;
      stageFlow: string;
      state: string;
      supervisorTails: string;
    };
  };
  settings: {
    actions: Record<'apply' | 'preview', string>;
    examples: string[];
    fields: {
      agentProfile: string;
      applied: string;
      approved: string;
      behavior: string;
      currencies: string;
      exchanges: string;
      instructionExamples: string;
      instructionRationale: string;
      instructionSummary: string;
      mode: string;
      regions: string;
      requiresConfirmation: string;
      risk: string;
      sectors: string;
      shouldUpdatePreferences: string;
      strictness: string;
      style: string;
      tone: string;
    };
    instructionEmpty: string;
    modeOptions: Record<'apply' | 'preview', string>;
    panels: {
      composer: string;
      operatorInstruction: string;
      preferences: string;
      recentRuns: string;
    };
    placeholder: string;
    recentRunsEmpty: string;
  };
  shell: {
    actions: {
      oneShot: string;
      refresh: string;
      restart: string;
      start: string;
      stop: string;
    };
    backend: string;
    eyebrow: string;
    language: string;
    lastRefresh: string;
    loading: string;
    loadingDetail: string;
    loadingElapsed: (seconds: number) => string;
    mode: string;
    navAria: string;
    runtime: string;
    runtimeUnavailable: string;
    subtitle: string;
    title: string;
    unavailable: string;
  };
  tabs: Record<TabId, string>;
};

export const CONTROL_ROOM_LOCALES: Array<{
  id: ControlRoomLocale;
  label: string;
}> = WEBGUI_LOCALE_OPTIONS;
