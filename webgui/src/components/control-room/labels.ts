import type { TabId } from '../control-room.helpers';
import {
  CONTROL_ROOM_COPY,
  CONTROL_ROOM_LOCALE_STORAGE_KEY,
  type ControlRoomCopy,
  type ControlRoomLocale,
} from './copy';
export { CONTROL_ROOM_LOCALE_STORAGE_KEY, CONTROL_ROOM_LOCALES } from './copy';
export type { ControlRoomCopy, ControlRoomLocale } from './copy';

const TAB_IDS: TabId[] = [
  'overview',
  'runtime',
  'portfolio',
  'proposals',
  'review',
  'memory',
  'chat',
  'settings',
];

/**
 * Normalize an arbitrary locale-ish value to a supported control-room locale.
 *
 * @param value - A stored locale, browser locale, or unknown input.
 * @returns A supported locale id, defaulting to English.
 */
export function normalizeControlRoomLocale(value: unknown): ControlRoomLocale {
  if (typeof value !== 'string') {
    return 'en';
  }
  const normalized = value.toLowerCase();
  if (normalized === 'tr' || normalized.startsWith('tr-')) {
    return 'tr';
  }
  return 'en';
}

export function initialControlRoomLocale(): ControlRoomLocale {
  if (globalThis.window === undefined) {
    return 'en';
  }
  try {
    const storedLocale = globalThis.window.localStorage.getItem(
      CONTROL_ROOM_LOCALE_STORAGE_KEY,
    );
    if (storedLocale) {
      return normalizeControlRoomLocale(storedLocale);
    }
  } catch {
    return 'en';
  }
  return normalizeControlRoomLocale(globalThis.window.navigator.language);
}

export function storeControlRoomLocale(locale: ControlRoomLocale): void {
  try {
    globalThis.window.localStorage.setItem(
      CONTROL_ROOM_LOCALE_STORAGE_KEY,
      locale,
    );
  } catch {
    // Ignore localStorage failures; the selected language still applies for this session.
  }
}

/**
 * Retrieve static copy for a supported control-room locale.
 *
 * @param locale - Locale id selected by the operator.
 * @returns The immutable copy catalog for the selected locale.
 */
export function getControlRoomCopy(locale: ControlRoomLocale): ControlRoomCopy {
  return CONTROL_ROOM_COPY[locale];
}

/**
 * Build localized tab descriptors while keeping the tab ids stable.
 *
 * @param copy - Control-room copy catalog.
 * @returns Stable tab id/label pairs for navigation.
 */
export function controlRoomTabs(copy: ControlRoomCopy) {
  return TAB_IDS.map((id) => ({ id, label: copy.tabs[id] }));
}
