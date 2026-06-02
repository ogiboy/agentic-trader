import { Globe2, Languages, type LucideIcon } from 'lucide-react';

import type { DocLanguage } from '@/lib/i18n/config';

export const languageLandingCopy = {
  root: {
    badge: 'Documentation',
    title: 'Choose your documentation language',
    description:
      'Agentic Trader docs now ship with English and Turkish entrypoints. Pick a language first, then continue into the same Fumadocs surface.',
  },
  docs: {
    badge: 'Docs routing',
    title: 'Docs now live under locale-aware routes',
    description:
      'Choose English or Turkish to open the full documentation tree. This keeps content, search, and navigation aligned for each language.',
  },
} as const;

export const languageCardCopy: Record<
  DocLanguage,
  {
    icon: LucideIcon;
    description: string;
    docsAction: string;
    homeAction: string;
  }
> = {
  en: {
    icon: Globe2,
    description:
      'Open the full documentation tree, landing page, and localized feedback messaging in English.',
    docsAction: 'Open docs',
    homeAction: 'Open home',
  },
  tr: {
    icon: Languages,
    description:
      'Tüm belge ağacını, başlangıç sayfasını ve yerelleştirilmiş geri bildirim akışını Türkçe olarak aç.',
    docsAction: 'Dokümanları aç',
    homeAction: 'Ana sayfayı aç',
  },
};
