export const WEBGUI_DEFAULT_LOCALE = 'en';
export const WEBGUI_LOCALE_COOKIE = 'agentic_trader_webgui_locale';
export const WEBGUI_LOCALE_STORAGE_KEY = 'agentic-trader-webgui-locale';

export const WEBGUI_LOCALES = ['en', 'tr'] as const;

export type WebguiLocale = (typeof WEBGUI_LOCALES)[number];

export const WEBGUI_LOCALE_OPTIONS: Array<{
  id: WebguiLocale;
  label: string;
}> = [
  { id: 'en', label: 'English' },
  { id: 'tr', label: 'Türkçe' },
];

export function normalizeWebguiLocale(value: unknown): WebguiLocale {
  if (typeof value !== 'string') {
    return WEBGUI_DEFAULT_LOCALE;
  }
  const normalized = value.toLowerCase();
  if (normalized === 'tr' || normalized.startsWith('tr-')) {
    return 'tr';
  }
  return WEBGUI_DEFAULT_LOCALE;
}
