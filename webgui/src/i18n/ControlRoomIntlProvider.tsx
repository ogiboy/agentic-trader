'use client';

import { NextIntlClientProvider } from 'next-intl';
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

import {
  WEBGUI_LOCALE_COOKIE,
  WEBGUI_LOCALE_STORAGE_KEY,
  normalizeWebguiLocale,
  type WebguiLocale,
} from './locales';
import { WEBGUI_MESSAGES } from './messages';

type WebguiLocaleContextValue = Readonly<{
  locale: WebguiLocale;
  selectLocale: (locale: WebguiLocale) => void;
}>;

const WebguiLocaleContext = createContext<WebguiLocaleContextValue | null>(
  null,
);

function persistLocale(locale: WebguiLocale): void {
  try {
    globalThis.window.localStorage?.setItem(WEBGUI_LOCALE_STORAGE_KEY, locale);
  } catch {
    // Locale still applies for this session if localStorage is unavailable.
  }
  if (globalThis.document) {
    globalThis.document.cookie = `${WEBGUI_LOCALE_COOKIE}=${locale}; Path=/; SameSite=Lax; Max-Age=31536000`;
  }
}

function storedLocalePreference(): WebguiLocale | null {
  try {
    const storedLocale = globalThis.window.localStorage?.getItem(
      WEBGUI_LOCALE_STORAGE_KEY,
    );
    return typeof storedLocale === 'string'
      ? normalizeWebguiLocale(storedLocale)
      : null;
  } catch {
    return null;
  }
}

export function useWebguiLocale(): readonly [
  WebguiLocale,
  (locale: WebguiLocale) => void,
] {
  const context = useContext(WebguiLocaleContext);
  if (!context) {
    throw new Error(
      'useWebguiLocale must be used inside ControlRoomIntlProvider',
    );
  }
  return [context.locale, context.selectLocale] as const;
}

export function ControlRoomIntlProvider({
  children,
  initialLocale,
}: Readonly<{
  children?: ReactNode;
  initialLocale: WebguiLocale;
}>) {
  const [locale, setLocale] = useState<WebguiLocale>(initialLocale);

  useEffect(() => {
    const localeTimer = globalThis.setTimeout(() => {
      const storedLocale = storedLocalePreference();
      if (storedLocale) {
        setLocale(storedLocale);
      }
    }, 0);
    return () => globalThis.clearTimeout(localeTimer);
  }, []);

  useEffect(() => {
    globalThis.document.documentElement.lang = locale;
    persistLocale(locale);
  }, [locale]);

  const selectLocale = useCallback((nextLocale: WebguiLocale) => {
    setLocale(nextLocale);
  }, []);

  const contextValue = useMemo(
    () => ({ locale, selectLocale }),
    [locale, selectLocale],
  );

  return (
    <WebguiLocaleContext.Provider value={contextValue}>
      <NextIntlClientProvider
        locale={locale}
        messages={WEBGUI_MESSAGES[locale]}
      >
        {children}
      </NextIntlClientProvider>
    </WebguiLocaleContext.Provider>
  );
}
