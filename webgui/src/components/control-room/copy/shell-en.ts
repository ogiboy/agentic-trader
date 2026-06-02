import type { ControlRoomCopy } from './types';

export const EN_SHELL_COPY = {
  actions: {
    oneShot: 'One Shot',
    refresh: 'Refresh',
    restart: 'Restart',
    start: 'Start',
    stop: 'Stop',
  },
  backend: 'Backend',
  eyebrow: 'Local-first control room',
  language: 'Language',
  lastRefresh: 'Last refresh',
  loading: 'Loading dashboard...',
  loadingDetail:
    'Collecting local runtime, broker, model, tool, and research status. Slow provider checks can take a few seconds.',
  loadingElapsed: (seconds) => `Waiting ${seconds}s`,
  mode: 'Mode',
  navAria: 'Sections',
  runtime: 'Runtime',
  runtimeUnavailable: 'runtime unavailable',
  subtitle: 'Paper-first. Strict. Inspectable.',
  title: 'Agentic Trader',
  unavailable: 'Dashboard unavailable.',
} satisfies ControlRoomCopy['shell'];

export const EN_TABS_COPY = {
  overview: 'Overview',
  runtime: 'Runtime',
  portfolio: 'Portfolio',
  proposals: 'Proposals',
  review: 'Review',
  memory: 'Decision Evidence',
  chat: 'Chat',
  settings: 'Settings',
} satisfies ControlRoomCopy['tabs'];
