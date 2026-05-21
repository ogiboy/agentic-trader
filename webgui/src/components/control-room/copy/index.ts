import { EN_CONTROL_ROOM_COPY } from './en';
import { TR_CONTROL_ROOM_COPY } from './tr';
import type { ControlRoomCopy, ControlRoomLocale } from './types';

export { CONTROL_ROOM_LOCALES, CONTROL_ROOM_LOCALE_STORAGE_KEY } from './types';
export type { ControlRoomCopy, ControlRoomLocale } from './types';

export const CONTROL_ROOM_COPY: Record<ControlRoomLocale, ControlRoomCopy> = {
  en: EN_CONTROL_ROOM_COPY,
  tr: TR_CONTROL_ROOM_COPY,
};
