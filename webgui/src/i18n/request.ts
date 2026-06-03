import { cookies } from 'next/headers';
import { getRequestConfig } from 'next-intl/server';

import { WEBGUI_LOCALE_COOKIE, normalizeWebguiLocale } from './locales';
import { WEBGUI_MESSAGES } from './messages';

export default getRequestConfig(async () => {
  const cookieStore = await cookies();
  const locale = normalizeWebguiLocale(
    cookieStore.get(WEBGUI_LOCALE_COOKIE)?.value,
  );

  return {
    locale,
    messages: WEBGUI_MESSAGES[locale],
  };
});
