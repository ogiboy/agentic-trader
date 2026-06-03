import { useEffect, useState } from 'react';

import { useWebguiLocale } from '@/i18n/ControlRoomIntlProvider';
import type { WebguiLocale } from '@/i18n/locales';

export function useControlRoomLocaleState(): readonly [
  WebguiLocale,
  (nextLocale: WebguiLocale) => void,
] {
  return useWebguiLocale();
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
