import type { DocLanguage } from '@/lib/i18n/config';
import { homeContentEn } from '@/lib/home/content/en';
import { homeContentTr } from '@/lib/home/content/tr';

export { type HomeContent } from '@/lib/home/content/types';
export type { HomeEntryPoint, WorkflowTrack } from '@/lib/home/content/types';

export function getHomeContent(locale: DocLanguage) {
  return locale === 'tr' ? homeContentTr : homeContentEn;
}
