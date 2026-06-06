export const uiLocaleEnv = "AGENTIC_TRADER_UI_LOCALE";

export const dashboardPages = Object.freeze([
  "overview",
  "runtime",
  "portfolio",
  "review",
  "memory",
  "chat",
  "settings",
]);

export const chatPersonas = Object.freeze([
  "operator_liaison",
  "regime_analyst",
  "strategy_selector",
  "risk_steward",
  "portfolio_manager",
]);

export const instructionModes = Object.freeze(["preview", "apply"]);

const enCopy = Object.freeze({
  chatSending: "Sending message to the operator surface...",
  chatPage: {
    completedDetail: "Completed Detail",
    composer: "COMPOSER",
    currentStage: "Current Stage",
    decisionWorkflow: "DECISION WORKFLOW",
    lastCompleted: "Last Completed",
    noChatMessages: "No chat messages yet.",
    noStageTimeline: "No stage timeline recorded yet.",
    outcome: "Outcome",
    outcomeType: "Outcome Type",
    operatorChat: "OPERATOR CHAT",
    ready: "Ready.",
    reasoningTools: "REASONING / TOOLS",
    reviewWarnings: "Review Warnings",
    role: "Role",
    stageDetail: "Stage Detail",
    stageStatus: "Stage Status",
    toolRoles: "Tool Roles",
    memoryRoles: "Memory Roles",
    typeDirectly:
      "Type directly to write. Enter sends. Backspace deletes. [ and ] switch persona.",
    user: "you",
    waitingOutcome: "Waiting for a completed symbol or service result.",
  },
  cliExecutableLabel: "CLI executable",
  cliExecutionUnavailable: "No CLI command could be executed.",
  connectingTo: "Connecting to {executable}...",
  dashboardTitle: "AGENTIC TRADER // INK CONTROL ROOM",
  emptyValue: "-",
  errorLabel: "Error",
  globalShortcutHelp:
    "r refresh  o one-shot  s start  x stop  R restart  q quit",
  instructionApplied: "Operator instruction applied to preferences.",
  instructionFailed: "Instruction failed.",
  instructionParsed: "Operator instruction parsed.",
  lastRefresh: "Last refresh",
  pageLabels: {
    overview: "Overview",
    runtime: "Runtime",
    portfolio: "Portfolio",
    review: "Review",
    memory: "Decision Evidence",
    chat: "Chat",
    settings: "Settings",
  },
  personaLabels: {
    operator_liaison: "Operator Assistant",
    regime_analyst: "Market Regime Analyst",
    strategy_selector: "Strategy Selector",
    risk_steward: "Risk Steward",
    portfolio_manager: "Portfolio Manager",
  },
  ready: "Ready.",
  settingsPage: {
    agentProfile: "Agent Profile",
    agentTone: "Agent Tone",
    behavior: "Behavior",
    composer: "COMPOSER",
    currencies: "Currencies",
    currenciesSectors: "Currencies / Sectors",
    enterSubmit: "Enter submit  |  [ ] switch mode",
    exchanges: "Exchanges",
    intervention: "Intervention",
    mode: "Mode",
    notes: "Notes",
    operatorInstruction: "OPERATOR INSTRUCTION",
    preferences: "PREFERENCES",
    preferencesUnavailable: "Preferences are temporarily unavailable.",
    profileTone: "Profile / Tone",
    recentRuns: "RECENT RUNS",
    regions: "Regions",
    regionsExchanges: "Regions / Exchanges",
    risk: "Risk",
    riskStyle: "Risk / Style",
    sectors: "Sectors",
    strictness: "Strictness",
    style: "Style",
    behaviorStrictness: "Behavior / Strictness",
    typeInstruction: "(type a safe operator instruction here)",
    working: "Working...",
  },
  unknown: "Unknown",
  working: "working...",
});

const trCopy = Object.freeze({
  chatSending: "Operatör yüzeyine mesaj gönderiliyor...",
  chatPage: {
    completedDetail: "Tamamlanan Detay",
    composer: "COMPOSER",
    currentStage: "Güncel Aşama",
    decisionWorkflow: "KARAR AKIŞI",
    lastCompleted: "Son Tamamlanan",
    noChatMessages: "Henüz sohbet mesajı yok.",
    noStageTimeline: "Henüz aşama zaman çizelgesi yok.",
    outcome: "Sonuç",
    outcomeType: "Sonuç Türü",
    operatorChat: "OPERATÖR SOHBETİ",
    ready: "Hazır.",
    reasoningTools: "AKIL YÜRÜTME / ARAÇLAR",
    reviewWarnings: "İnceleme Uyarıları",
    role: "Rol",
    stageDetail: "Aşama Detayı",
    stageStatus: "Aşama Durumu",
    toolRoles: "Araç Rolleri",
    memoryRoles: "Hafıza Rolleri",
    typeDirectly:
      "Doğrudan yaz. Enter gönderir. Backspace siler. [ ve ] persona değiştirir.",
    user: "sen",
    waitingOutcome: "Tamamlanmış sembol veya servis sonucu bekleniyor.",
  },
  cliExecutableLabel: "CLI çalıştırıcı",
  cliExecutionUnavailable: "CLI komutu çalıştırılamadı.",
  connectingTo: "{executable} bağlantısı kuruluyor...",
  dashboardTitle: "AGENTIC TRADER // INK KONTROL ODASI",
  emptyValue: "-",
  errorLabel: "Hata",
  globalShortcutHelp:
    "r yenile  o tek-sefer  s başlat  x durdur  R yeniden başlat  q çık",
  instructionApplied: "Operatör talimatı tercihlere uygulandı.",
  instructionFailed: "Talimat başarısız oldu.",
  instructionParsed: "Operatör talimatı çözümlendi.",
  lastRefresh: "Son yenileme",
  pageLabels: {
    overview: "Genel Bakış",
    runtime: "Çalışma",
    portfolio: "Portföy",
    review: "İnceleme",
    memory: "Karar Kanıtı",
    chat: "Sohbet",
    settings: "Ayarlar",
  },
  personaLabels: {
    operator_liaison: "Operatör Asistanı",
    regime_analyst: "Piyasa Rejimi Analisti",
    strategy_selector: "Strateji Seçici",
    risk_steward: "Risk Sorumlusu",
    portfolio_manager: "Portföy Yöneticisi",
  },
  ready: "Hazır.",
  settingsPage: {
    agentProfile: "Ajan Profili",
    agentTone: "Ajan Tonu",
    behavior: "Davranış",
    composer: "COMPOSER",
    currencies: "Para Birimleri",
    currenciesSectors: "Para Birimleri / Sektörler",
    enterSubmit: "Enter gönder  |  [ ] mod değiştir",
    exchanges: "Borsalar",
    intervention: "Müdahale",
    mode: "Mod",
    notes: "Notlar",
    operatorInstruction: "OPERATÖR TALİMATI",
    preferences: "TERCİHLER",
    preferencesUnavailable: "Tercihler geçici olarak kullanılamıyor.",
    profileTone: "Profil / Ton",
    recentRuns: "SON RUN'LAR",
    regions: "Bölgeler",
    regionsExchanges: "Bölgeler / Borsalar",
    risk: "Risk",
    riskStyle: "Risk / Stil",
    sectors: "Sektörler",
    strictness: "Katılık",
    style: "Stil",
    behaviorStrictness: "Davranış / Katılık",
    typeInstruction: "(buraya güvenli bir operatör talimatı yaz)",
    working: "Çalışıyor...",
  },
  unknown: "Bilinmiyor",
  working: "çalışıyor...",
});

export const tuiCopyByLocale = Object.freeze({
  en: enCopy,
  tr: trCopy,
});

export function normalizeTuiLocale(locale) {
  if (typeof locale !== "string") {
    return "en";
  }
  const normalized = locale.toLowerCase();
  return normalized === "tr" || normalized.startsWith("tr-") ? "tr" : "en";
}

export function getTuiCopy(locale = process.env[uiLocaleEnv]) {
  return tuiCopyByLocale[normalizeTuiLocale(locale)];
}

export const tuiCopy = getTuiCopy();
export const dashboardTitle = tuiCopy.dashboardTitle;
export const pageLabels = tuiCopy.pageLabels;
export const personaLabels = tuiCopy.personaLabels;
export const globalShortcutHelp = tuiCopy.globalShortcutHelp;
export const cliExecutionUnavailable = tuiCopy.cliExecutionUnavailable;

/**
 * Format a persona key into its human-readable label.
 * @param {string} value - Persona key to format (may be falsy).
 * @returns {string} `personaLabels[value]` if present; otherwise `value` if truthy; otherwise `'-'`.
 */
export function formatPersona(value, copy = tuiCopy) {
  return copy.personaLabels[value] || value || copy.emptyValue;
}

/**
 * Resolve a human-readable label for a dashboard page key.
 * @param {string} page - Page key to resolve (e.g., "overview", "runtime").
 * @returns {string} The display label for the page, or `'Unknown'` if the key is not recognized.
 */
export function getPageLabel(page, copy = tuiCopy) {
  return copy.pageLabels[page] || copy.unknown;
}

/**
 * Map a numeric page shortcut to its dashboard page key.
 * @param {string|number} input - The numeric shortcut (e.g., "1" or 1) representing a 1-based page index.
 * @returns {string|undefined} The page key for the given shortcut, or `undefined` if the input is not a valid 1-based index.
 */
export function getPageForShortcut(input) {
  const pageNumber = Number.parseInt(input, 10);
  if (
    !Number.isInteger(pageNumber) ||
    pageNumber < 1 ||
    pageNumber > dashboardPages.length
  ) {
    return undefined;
  }
  return dashboardPages[pageNumber - 1];
}

/**
 * Build a help string that maps each dashboard page to its 1-based numeric shortcut.
 *
 * @returns {string} A string of pairs in the form `"index pageKey"` for each dashboard page, with pairs separated by two spaces (e.g. `"1 overview  2 runtime"`).
 */
export function getPageShortcutHelp() {
  return dashboardPages.map((page, index) => `${index + 1} ${page}`).join("  ");
}

/**
 * Selects an element from an array by rotating the index of a given current value by an offset with wraparound.
 * @param {Array} values - Ordered list of values to rotate within.
 * @param {*} current - The current value whose index is used as the rotation base. If not found, behaves as if index is -1.
 * @param {number} offset - Number of positions to move from the current index; may be negative.
 * @returns {*} The value at the rotated index within `values`.
 */
function rotateValue(values, current, offset) {
  return values[
    (values.indexOf(current) + offset + values.length) % values.length
  ];
}

/**
 * Move the current chat persona by the given offset within the ordered persona list, wrapping around.
 *
 * @param {string} current - The current persona key.
 * @param {number} offset - Number of positions to move (positive or negative).
 * @returns {string|undefined} The persona key at the new position, or `undefined` if `current` is not in the persona list.
 */
export function rotatePersona(current, offset) {
  return rotateValue(chatPersonas, current, offset);
}

/**
 * Cycle the current instruction mode by a given offset within the available modes.
 *
 * @param {string} current - The currently active instruction mode.
 * @param {number} offset - The signed number of positions to move (positive or negative).
 * @returns {string} The instruction mode at the resulting position, wrapping around the available modes.
 */
export function rotateInstructionMode(current, offset) {
  return rotateValue(instructionModes, current, offset);
}

/**
 * Build a single-line dashboard status string showing the current page, shortcut help, and an optional working indicator.
 * @param {{busy?: boolean, page?: string}} params
 * @param {boolean} [params.busy=false] - If true, append "  |  working..." to the end of the status line.
 * @param {string} [params.page] - Current page key (one of the values in dashboardPages); used to compute the 1-based page index and label.
 * @returns {string} A status line like "page {index}/{total}: {label}  |  {pageShortcuts}  |  {globalShortcutHelp}" with "  |  working..." appended when `busy` is true.
 */
export function dashboardStatusLine({ busy = false, page, copy = tuiCopy }) {
  const pageIndex = dashboardPages.indexOf(page) + 1;
  const pageLabel = getPageLabel(page, copy);
  const workingSuffix = busy ? `  |  ${copy.working}` : "";

  return `page ${pageIndex}/${dashboardPages.length}: ${pageLabel}  |  ${getPageShortcutHelp()}  |  ${copy.globalShortcutHelp}${workingSuffix}`;
}
