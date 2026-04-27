import type { DocLanguage } from '@/lib/i18n/config';
import { source } from '@/lib/source';

export function getDocPage(slug: string[], locale: DocLanguage) {
  return source.getPage(slug, locale);
}
