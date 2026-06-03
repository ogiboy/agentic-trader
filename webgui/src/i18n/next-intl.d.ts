import { EN_MESSAGES } from './messages';
import { routing } from './routing';

declare module 'next-intl' {
  interface AppConfig {
    Locale: (typeof routing.locales)[number];
    Messages: typeof EN_MESSAGES;
  }
}
