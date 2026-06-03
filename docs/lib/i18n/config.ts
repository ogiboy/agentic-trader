import { defineI18n } from 'fumadocs-core/i18n';
import type { Metadata } from 'next';

export const docLanguages = ['en', 'tr'] as const;
export type DocLanguage = (typeof docLanguages)[number];

export const defaultLanguage: DocLanguage = 'en';

export const languageLabels: Record<DocLanguage, string> = {
  en: 'English',
  tr: 'Türkçe',
};

export const i18n = defineI18n({
  defaultLanguage,
  languages: [...docLanguages],
  parser: 'dir',
});

const homeMetadata: Record<DocLanguage, Metadata> = {
  en: {
    title: 'Agentic Trader Docs',
    description:
      'Developer documentation for the local-first Agentic Trader runtime, operator surfaces, and QA workflow.',
  },
  tr: {
    title: 'Agentic Trader Dokümantasyonu',
    description:
      "Local-first Agentic Trader runtime'ı, operatör yüzeyleri ve kalite akışı için geliştirici dokümantasyonu.",
  },
};

/**
 * Retrieve homepage metadata localized for the specified documentation language.
 *
 * @param locale - The documentation language to select (`'en'` or `'tr'`).
 * @returns The `Metadata` object for the given language.
 */
export function getHomeMetadata(locale: DocLanguage): Metadata {
  return homeMetadata[locale];
}

/**
 * Resolves a locale string to a supported documentation language.
 *
 * @param value - Locale string to resolve
 * @returns The `DocLanguage` matching `value` if supported, otherwise the default language
 */
export function getDocLanguage(value: string): DocLanguage {
  return docLanguages.includes(value as DocLanguage)
    ? (value as DocLanguage)
    : defaultLanguage;
}
