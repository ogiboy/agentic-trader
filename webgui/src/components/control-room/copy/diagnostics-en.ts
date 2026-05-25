import type { ControlRoomCopy } from './types';

export const EN_DIAGNOSTICS_COPY = {
  values: {
    active: 'active',
    available: 'available',
    clear: 'clear',
    configured: 'configured',
    disabledByOwnership: 'disabled by ownership',
    enabled: 'enabled',
    inactive: 'inactive',
    missing: 'missing',
    no: 'no',
    requested: 'requested',
    yes: 'yes',
  },
  labels: {
    alpacaKey: 'Alpaca Key',
    backend: 'Backend',
    baseUrl: 'Base URL',
    brokerBackend: 'Broker Backend',
    brokerHealth: 'Broker Health',
    brokerState: 'Broker State',
    camofox: 'Camofox',
    camofoxAccessKey: 'Camofox Access Key',
    camofoxBlocker: 'Camofox Blocker',
    camofoxOwned: 'Camofox Owned',
    camofoxOwnership: 'Camofox Ownership',
    camofoxReachable: 'Camofox Reachable',
    camofoxService: 'Camofox Service',
    camofoxUrl: 'Camofox URL',
    canRunLocalPaperCycle: 'Can run local paper cycle',
    canUseAlpacaPaper: 'Can use Alpaca paper',
    executionMode: 'Execution Mode',
    externalPaperModeActive: 'External paper mode active',
    finnhubKey: 'Finnhub Key',
    firecrawlOwnership: 'Firecrawl Ownership',
    firecrawlRuntime: 'Firecrawl Runtime',
    fmpKey: 'FMP Key',
    freshSources: 'fresh',
    killSwitch: 'Kill Switch',
    llmReachable: 'LLM Reachable',
    llmRuntime: 'LLM Runtime',
    marketProvider: 'Market Provider',
    marketRole: 'Market Role',
    marketSession: 'Market Session',
    model: 'Model',
    modelAdapter: 'Model Adapter',
    modelAvailable: 'Model Available',
    modelService: 'Model Service',
    modelServiceOwned: 'Model Service Owned',
    modelServiceReachable: 'Model Service Reachable',
    modelServiceUrl: 'Model Service URL',
    newsMode: 'News Mode',
    ollamaOwnership: 'Ollama Ownership',
    ollamaReachable: 'Ollama Reachable',
    provider: 'Provider',
    research: 'Research',
    researchControl: 'Research Control',
    researchDigestReplay: 'Research Digest Replay',
    researchSources: 'Research Sources',
    researchTrigger: 'Research Trigger',
    sourceMissing: 'missing',
    sourceUnknown: 'unknown',
    webGui: 'Web GUI',
    webGuiOwned: 'Web GUI Owned',
    webGuiService: 'Web GUI Service',
    webGuiUrl: 'Web GUI URL',
    whyAlpacaPaperBlocked: 'Why Alpaca paper is blocked',
    whyPaperCycleBlocked: 'Why paper cycle is blocked',
  },
  messages: {
    appOwnedRuntime: 'app-owned',
    camofoxAccessKeyMissing:
      'set CAMOFOX_ACCESS_KEY or CAMOFOX_API_KEY in ignored local env before start',
    firecrawlRuntime: 'internal SDK first; host CLI fallback',
    internalFirstRuntime: 'internal-first',
    noProviderWarnings: 'No provider warnings.',
    status: {
      alpacaPaperReady: 'Alpaca paper adapter is configured for paper trading.',
      camofoxReachable:
        'Camofox server is reachable; browser launches on demand.',
      modelServiceHostDefault:
        'Ollama is reachable. This is a host/default Ollama service; model-service stop will not kill it.',
      noRuntimeState: 'No runtime state has been recorded yet.',
      webGuiStateStale:
        'Recorded Web GUI state is stale or process ownership could not be verified.',
    },
  },
  actions: {
    camofoxAccessKeyMissing:
      'Camofox access key is missing. Add CAMOFOX_ACCESS_KEY or CAMOFOX_API_KEY in local env before start.',
    camofoxAppManagedNotRunning:
      'Camofox is app-managed but not running. Start it from Camofox.',
    camofoxHostManagedUnreachable:
      'Camofox is host-managed but unreachable. Start the host helper or switch to App Tools.',
    camofoxOwnershipUndecided:
      'Camofox ownership is undecided. Choose App Tools or Host Fallback.',
    ollamaAppManagedNotRunning:
      'Ollama is app-managed but not running. Start it from Ollama.',
    ollamaHostManagedUnreachable:
      'Ollama is host-managed but unreachable. Start it on the host or switch to App Tools.',
    ollamaModelMissing: (model) => {
      const displayModel =
        typeof model === 'string' ||
        typeof model === 'number' ||
        typeof model === 'boolean'
          ? String(model)
          : 'the configured model';
      return `Ollama is reachable but ${displayModel} is not available yet.`;
    },
    ollamaOwnershipUndecided:
      'Ollama ownership is undecided. Choose App Tools or Host Fallback before first run.',
  },
} satisfies ControlRoomCopy['diagnostics'];
