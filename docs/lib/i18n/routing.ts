import {
  defaultLanguage,
  docLanguages,
  type DocLanguage,
} from '@/lib/i18n/config';

export function isDocLanguage(value: string): value is DocLanguage {
  return docLanguages.includes(value as DocLanguage);
}

export function getDocLanguage(value?: string): DocLanguage {
  if (value && isDocLanguage(value)) {
    return value;
  }

  return defaultLanguage;
}

export function withLanguagePrefix(
  locale: DocLanguage,
  path: `/${string}`,
): string {
  if (path === '/') {
    return `/${locale}`;
  }

  return `/${locale}${path}`;
}
