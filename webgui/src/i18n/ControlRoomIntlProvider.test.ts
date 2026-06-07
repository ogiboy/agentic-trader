// @vitest-environment jsdom

import { act, cleanup, render, screen } from '@testing-library/react';
import React from 'react';
import { afterEach, describe, expect, it } from 'vitest';

import {
  ControlRoomIntlProvider,
  useWebguiLocale,
} from './ControlRoomIntlProvider';
import { WEBGUI_LOCALE_COOKIE, WEBGUI_LOCALE_STORAGE_KEY } from './locales';

const localStorageDescriptor = Object.getOwnPropertyDescriptor(
  globalThis.window,
  'localStorage',
);

function LocaleProbe() {
  const [locale] = useWebguiLocale();
  return React.createElement('output', { 'aria-label': 'locale' }, locale);
}

function withIntl(initialLocale: 'en' | 'tr') {
  return React.createElement(
    ControlRoomIntlProvider,
    { initialLocale },
    React.createElement(LocaleProbe),
  );
}

function installLocalStorage(initialEntries: Record<string, string> = {}) {
  const storage = new Map(Object.entries(initialEntries));
  const localStorage = {
    clear: () => storage.clear(),
    getItem: (key: string) => storage.get(key) ?? null,
    key: (index: number) => Array.from(storage.keys())[index] ?? null,
    removeItem: (key: string) => {
      storage.delete(key);
    },
    setItem: (key: string, value: string) => {
      storage.set(key, value);
    },
    get length() {
      return storage.size;
    },
  } as unknown as Storage;
  Object.defineProperty(globalThis.window, 'localStorage', {
    configurable: true,
    value: localStorage,
  });
}

async function flushLocaleTimer() {
  await act(async () => {
    await new Promise((resolve) => globalThis.setTimeout(resolve, 0));
  });
}

afterEach(() => {
  cleanup();
  if (localStorageDescriptor) {
    Object.defineProperty(
      globalThis.window,
      'localStorage',
      localStorageDescriptor,
    );
  } else {
    Reflect.deleteProperty(globalThis.window, 'localStorage');
  }
  globalThis.document.cookie = `${WEBGUI_LOCALE_COOKIE}=; Path=/; Max-Age=0`;
  globalThis.document.documentElement.lang = '';
});

describe('ControlRoomIntlProvider', () => {
  it('preserves the initial locale when localStorage has no saved preference', async () => {
    installLocalStorage();

    render(withIntl('tr'));
    await flushLocaleTimer();

    expect(screen.getByLabelText('locale').textContent).toBe('tr');
    expect(globalThis.document.documentElement.lang).toBe('tr');
    expect(
      globalThis.window.localStorage.getItem(WEBGUI_LOCALE_STORAGE_KEY),
    ).toBe('tr');
    expect(globalThis.document.cookie).toContain(`${WEBGUI_LOCALE_COOKIE}=tr`);
  });

  it('keeps the active locale when localStorage is inaccessible', async () => {
    Object.defineProperty(globalThis.window, 'localStorage', {
      configurable: true,
      value: {
        getItem: () => {
          throw new Error('localStorage blocked');
        },
        setItem: () => {
          throw new Error('localStorage blocked');
        },
      } as unknown as Storage,
    });

    render(withIntl('tr'));
    await flushLocaleTimer();

    expect(screen.getByLabelText('locale').textContent).toBe('tr');
    expect(globalThis.document.documentElement.lang).toBe('tr');
    expect(globalThis.document.cookie).toContain(`${WEBGUI_LOCALE_COOKIE}=tr`);
  });
});
