import { i18n, languageLabels, type DocLanguage } from '@/lib/i18n/config';
import { withLanguagePrefix } from '@/lib/i18n/routing';
import { i18nProvider, uiTranslations } from 'fumadocs-ui/i18n';
import type { BaseLayoutProps } from 'fumadocs-ui/layouts/shared';
import { ChartCandlestick } from 'lucide-react';

const translations = i18n
  .translations()
  .extend(uiTranslations())
  .add('ui', {
    en: {
      displayName: languageLabels.en,
    },
    tr: {
      displayName: languageLabels.tr,
      search: 'Dokümanlarda ara',
    },
  });

export const i18nUI = {
  ...i18n,
  provider: (locale?: DocLanguage | (string & {})) =>
    i18nProvider(translations, locale),
};

/**
 * Build layout configuration for the documentation site tailored to the given locale.
 *
 * @param locale - Language code used to generate the localized navigation URL and UI provider context
 * @returns Layout properties including a localized navigation title URL and the repository URL
 */
export function baseOptions(locale: DocLanguage): BaseLayoutProps {
  return {
    nav: {
      title: (
        <span className='inline-flex items-center gap-2 font-medium'>
          <ChartCandlestick className='size-4' />
          Agentic Trader Docs
        </span>
      ),
      url: withLanguagePrefix(locale, '/'),
    },
    githubUrl: 'https://github.com/ogiboy/agentic-trader',
  };
}
