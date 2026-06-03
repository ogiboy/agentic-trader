import { defineRouting } from 'next-intl/routing';

import { WEBGUI_DEFAULT_LOCALE, WEBGUI_LOCALES } from './locales';

export const routing = defineRouting({
  defaultLocale: WEBGUI_DEFAULT_LOCALE,
  localePrefix: 'never',
  locales: WEBGUI_LOCALES,
});
