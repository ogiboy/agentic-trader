export const dashboardTitle = "AGENTIC TRADER // INK CONTROL ROOM";

export const dashboardPages = Object.freeze([
  "overview",
  "runtime",
  "portfolio",
  "review",
  "memory",
  "chat",
  "settings",
]);

export const pageLabels = Object.freeze({
  overview: "Overview",
  runtime: "Runtime",
  portfolio: "Portfolio",
  review: "Review",
  memory: "Decision Evidence",
  chat: "Chat",
  settings: "Settings",
});

export const chatPersonas = Object.freeze([
  "operator_liaison",
  "regime_analyst",
  "strategy_selector",
  "risk_steward",
  "portfolio_manager",
]);

export const personaLabels = Object.freeze({
  operator_liaison: "Operator Assistant",
  regime_analyst: "Market Regime Analyst",
  strategy_selector: "Strategy Selector",
  risk_steward: "Risk Steward",
  portfolio_manager: "Portfolio Manager",
});

export const instructionModes = Object.freeze(["preview", "apply"]);

export const globalShortcutHelp =
  "r refresh  o one-shot  s start  x stop  R restart  q quit";

export const cliExecutionUnavailable = "No CLI command could be executed.";

/**
 * Format a persona key into its human-readable label.
 * @param {string} value - Persona key to format (may be falsy).
 * @returns {string} `personaLabels[value]` if present; otherwise `value` if truthy; otherwise `'-'`.
 */
export function formatPersona(value) {
  return personaLabels[value] || value || "-";
}

/**
 * Resolve a human-readable label for a dashboard page key.
 * @param {string} page - Page key to resolve (e.g., "overview", "runtime").
 * @returns {string} The display label for the page, or `'Unknown'` if the key is not recognized.
 */
export function getPageLabel(page) {
  return pageLabels[page] || "Unknown";
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
export function dashboardStatusLine({ busy = false, page }) {
  const pageIndex = dashboardPages.indexOf(page) + 1;
  const pageLabel = getPageLabel(page);
  const workingSuffix = busy ? "  |  working..." : "";

  return `page ${pageIndex}/${dashboardPages.length}: ${pageLabel}  |  ${getPageShortcutHelp()}  |  ${globalShortcutHelp}${workingSuffix}`;
}
