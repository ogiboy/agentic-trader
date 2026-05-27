export const dashboardTitle = 'AGENTIC TRADER // INK CONTROL ROOM';

export const dashboardPages = Object.freeze([
  'overview',
  'runtime',
  'portfolio',
  'review',
  'memory',
  'chat',
  'settings',
]);

export const pageLabels = Object.freeze({
  overview: 'Overview',
  runtime: 'Runtime',
  portfolio: 'Portfolio',
  review: 'Review',
  memory: 'Decision Evidence',
  chat: 'Chat',
  settings: 'Settings',
});

export const chatPersonas = Object.freeze([
  'operator_liaison',
  'regime_analyst',
  'strategy_selector',
  'risk_steward',
  'portfolio_manager',
]);

export const personaLabels = Object.freeze({
  operator_liaison: 'Operator Assistant',
  regime_analyst: 'Market Regime Analyst',
  strategy_selector: 'Strategy Selector',
  risk_steward: 'Risk Steward',
  portfolio_manager: 'Portfolio Manager',
});

export const instructionModes = Object.freeze(['preview', 'apply']);

export const globalShortcutHelp =
  'r refresh  o one-shot  s start  x stop  R restart  q quit';

export function formatPersona(value) {
  return personaLabels[value] || value || '-';
}

export function getPageLabel(page) {
  return pageLabels[page] || 'Unknown';
}

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

export function getPageShortcutHelp() {
  return dashboardPages
    .map((page, index) => `${index + 1} ${page}`)
    .join('  ');
}

function rotateValue(values, current, offset) {
  return values[
    (values.indexOf(current) + offset + values.length) % values.length
  ];
}

export function rotatePersona(current, offset) {
  return rotateValue(chatPersonas, current, offset);
}

export function rotateInstructionMode(current, offset) {
  return rotateValue(instructionModes, current, offset);
}

export function dashboardStatusLine({ busy = false, page }) {
  const pageIndex = dashboardPages.indexOf(page) + 1;
  const pageLabel = getPageLabel(page);
  const workingSuffix = busy ? '  |  working...' : '';

  return `page ${pageIndex}/${dashboardPages.length}: ${pageLabel}  |  ${getPageShortcutHelp()}  |  ${globalShortcutHelp}${workingSuffix}`;
}
