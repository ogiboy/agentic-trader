import { useCallback, useEffect, useState } from 'react';

import {
  initialControlRoomLocale,
  storeControlRoomLocale,
  type ControlRoomLocale,
} from './labels';

export function useControlRoomLocaleState(): readonly [
  ControlRoomLocale,
  (nextLocale: ControlRoomLocale) => void,
] {
  const [locale, setLocale] = useState<ControlRoomLocale>('en');

  useEffect(() => {
    const localeTimer = globalThis.setTimeout(() => {
      setLocale(initialControlRoomLocale());
    }, 0);
    return () => globalThis.clearTimeout(localeTimer);
  }, []);

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  const selectLocale = useCallback((nextLocale: ControlRoomLocale): void => {
    setLocale(nextLocale);
    storeControlRoomLocale(nextLocale);
  }, []);

  return [locale, selectLocale] as const;
}

export function useLoadingSeconds(loading: boolean): number {
  const [loadingSeconds, setLoadingSeconds] = useState(0);

  useEffect(() => {
    if (!loading) {
      return undefined;
    }
    const startedAt = Date.now();
    const timer = globalThis.setInterval(() => {
      setLoadingSeconds(
        Math.max(0, Math.floor((Date.now() - startedAt) / 1000)),
      );
    }, 1000);
    return () => globalThis.clearInterval(timer);
  }, [loading]);

  return loadingSeconds;
}
