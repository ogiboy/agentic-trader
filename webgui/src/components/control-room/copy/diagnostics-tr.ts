import type { ControlRoomCopy } from './types';

export const TR_DIAGNOSTICS_COPY = {
  values: {
    active: 'aktif',
    available: 'var',
    clear: 'temiz',
    configured: 'ayarlı',
    disabledByOwnership: 'sahiplik seçimi nedeniyle kapalı',
    enabled: 'açık',
    inactive: 'pasif',
    missing: 'eksik',
    no: 'hayır',
    requested: 'istendi',
    yes: 'evet',
  },
  labels: {
    alpacaKey: 'Alpaca Anahtarı',
    backend: 'Backend',
    baseUrl: 'Temel URL',
    brokerBackend: 'Broker Backend',
    brokerHealth: 'Broker Sağlığı',
    brokerState: 'Broker Durumu',
    camofox: 'Camofox',
    camofoxAccessKey: 'Camofox Erişim Anahtarı',
    camofoxBlocker: 'Camofox Engeli',
    camofoxOwned: 'Camofox App Sahipliğinde',
    camofoxOwnership: 'Camofox Sahipliği',
    camofoxReachable: 'Camofox Erişilebilir',
    camofoxService: 'Camofox Servisi',
    camofoxUrl: 'Camofox URL',
    canRunLocalPaperCycle: 'Yerel paper döngüsü çalışabilir',
    canUseAlpacaPaper: 'Alpaca paper kullanılabilir',
    executionMode: 'İşlem Modu',
    externalPaperModeActive: 'Harici paper modu aktif',
    finnhubKey: 'Finnhub Anahtarı',
    firecrawlOwnership: 'Firecrawl Sahipliği',
    firecrawlRuntime: 'Firecrawl Çalışma Biçimi',
    fmpKey: 'FMP Anahtarı',
    freshSources: 'güncel',
    killSwitch: 'Kill Switch',
    llmReachable: 'LLM Erişilebilir',
    llmRuntime: 'LLM Çalışma Biçimi',
    marketProvider: 'Piyasa Sağlayıcısı',
    marketRole: 'Piyasa Rolü',
    marketSession: 'Piyasa Seansı',
    model: 'Model',
    modelAdapter: 'Model Adaptörü',
    modelAvailable: 'Model Var',
    modelService: 'Model Servisi',
    modelServiceOwned: 'Model Servisi App Sahipliğinde',
    modelServiceReachable: 'Model Servisi Erişilebilir',
    modelServiceUrl: 'Model Servisi URL',
    newsMode: 'Haber Modu',
    ollamaOwnership: 'Ollama Sahipliği',
    ollamaReachable: 'Ollama Erişilebilir',
    provider: 'Sağlayıcı',
    research: 'Araştırma',
    researchControl: 'Araştırma Kontrolü',
    researchDigestReplay: 'Araştırma Özeti Tekrarı',
    researchSources: 'Araştırma Kaynakları',
    researchTrigger: 'Araştırma Tetikleme',
    sourceMissing: 'eksik',
    sourceUnknown: 'bilinmeyen',
    webGui: 'Web GUI',
    webGuiOwned: 'Web GUI App Sahipliğinde',
    webGuiService: 'Web GUI Servisi',
    webGuiUrl: 'Web GUI URL',
    whyAlpacaPaperBlocked: 'Alpaca paper neden bloklu',
    whyPaperCycleBlocked: 'Paper döngüsü neden bloklu',
  },
  messages: {
    appOwnedRuntime: 'uygulama sahipliğinde',
    camofoxAccessKeyMissing:
      'başlatmadan önce ignored local env içine CAMOFOX_ACCESS_KEY veya CAMOFOX_API_KEY ekle',
    firecrawlRuntime: 'önce dahili SDK; gerekirse host CLI yedeği',
    internalFirstRuntime: 'önce dahili',
    noProviderWarnings: 'Sağlayıcı uyarısı yok.',
    status: {
      alpacaPaperReady:
        'Alpaca paper adaptörü paper işlem için yapılandırıldı.',
      camofoxReachable:
        'Camofox sunucusu erişilebilir; tarayıcı gerektiğinde başlatılır.',
      modelServiceHostDefault:
        'Ollama erişilebilir. Bu host/default Ollama servisidir; model-service stop bunu durdurmaz.',
      noRuntimeState: 'Henüz çalışma durumu kaydedilmedi.',
      webGuiStateStale:
        'Kayıtlı Web GUI durumu eski veya süreç sahipliği doğrulanamadı.',
    },
  },
  actions: {
    camofoxAccessKeyMissing:
      'Camofox erişim anahtarı eksik. Başlatmadan önce local env içine CAMOFOX_ACCESS_KEY veya CAMOFOX_API_KEY ekle.',
    camofoxAppManagedNotRunning:
      'Camofox app-managed seçili ama çalışmıyor. Camofox üzerinden başlat.',
    camofoxHostManagedUnreachable:
      'Camofox host-managed seçili ama erişilemiyor. Host helperı başlat veya App Araçlarına geç.',
    camofoxOwnershipUndecided:
      'Camofox sahipliği kararsız. App Araçları veya Host Yedeği seç.',
    ollamaAppManagedNotRunning:
      'Ollama app-managed seçili ama çalışmıyor. Ollama üzerinden başlat.',
    ollamaHostManagedUnreachable:
      'Ollama host-managed seçili ama erişilemiyor. Host üzerinde başlat veya App Araçlarına geç.',
    ollamaModelMissing: (model) => {
      const displayModel =
        typeof model === 'string' ||
        typeof model === 'number' ||
        typeof model === 'boolean'
          ? String(model)
          : 'ayarlı model';
      return `Ollama erişilebilir ama ${displayModel} henüz yok.`;
    },
    ollamaOwnershipUndecided:
      'Ollama sahipliği kararsız. İlk çalıştırmadan önce App Araçları veya Host Yedeği seç.',
  },
} satisfies ControlRoomCopy['diagnostics'];
