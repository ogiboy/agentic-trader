import type { Metadata } from 'next';
import { defineI18n } from 'fumadocs-core/i18n';

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

export function getHomeMetadata(locale: DocLanguage): Metadata {
  return locale === 'en'
    ? {
        title: 'Agentic Trader Docs',
        description:
          'Developer documentation for the local-first Agentic Trader runtime, operator surfaces, and QA workflow.',
      }
    : {
        title: 'Agentic Trader Dokümantasyonu',
        description:
          "Local-first Agentic Trader runtime'ı, operatör yüzeyleri ve kalite akışı için geliştirici dokümantasyonu.",
      };
}

export function getDocLanguage(value: string): DocLanguage {
  return docLanguages.includes(value as DocLanguage)
    ? (value as DocLanguage)
    : defaultLanguage;
}
