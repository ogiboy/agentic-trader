import { describe, expect, it } from 'vitest';

import {
  CONTROL_ROOM_LOCALES,
  controlRoomTabs,
  getControlRoomCopy,
  normalizeControlRoomLocale,
} from './labels';

describe('control-room labels', () => {
  it('normalizes unsupported or regional locale values safely', () => {
    expect(normalizeControlRoomLocale('tr-TR')).toBe('tr');
    expect(normalizeControlRoomLocale('en-US')).toBe('en');
    expect(normalizeControlRoomLocale(null)).toBe('en');
  });

  it('keeps tab ids stable while localizing labels', () => {
    const englishTabs = controlRoomTabs(getControlRoomCopy('en'));
    const turkishTabs = controlRoomTabs(getControlRoomCopy('tr'));

    expect(englishTabs.map((tab) => tab.id)).toEqual(
      turkishTabs.map((tab) => tab.id),
    );
    expect(englishTabs.find((tab) => tab.id === 'overview')?.label).toBe(
      'Overview',
    );
    expect(turkishTabs.find((tab) => tab.id === 'overview')?.label).toBe(
      'Özet',
    );
  });

  it('uses product-facing locale names', () => {
    expect(CONTROL_ROOM_LOCALES).toEqual([
      { id: 'en', label: 'English' },
      { id: 'tr', label: 'Türkçe' },
    ]);
  });

  it('localizes action feedback and current-cycle labels', () => {
    const englishCopy = getControlRoomCopy('en');
    const turkishCopy = getControlRoomCopy('tr');

    expect(englishCopy.feedback.dashboardRefreshed).toBe(
      'Dashboard refreshed.',
    );
    expect(turkishCopy.feedback.dashboardRefreshed).toBe(
      'Dashboard yenilendi.',
    );
    expect(englishCopy.currentCycle.currentSymbol).toBe('Current Symbol');
    expect(turkishCopy.currentCycle.currentSymbol).toBe('Güncel Sembol');
    expect(englishCopy.proposals.actions.approve.label).toBe('Approve');
    expect(turkishCopy.proposals.actions.approve.label).toBe('Onayla');
    expect(englishCopy.chat.placeholder).toContain('review');
    expect(turkishCopy.chat.placeholder).toContain('İnceleme');
    expect(englishCopy.settings.actions.apply).toBe('Apply');
    expect(turkishCopy.settings.actions.apply).toBe('Uygula');
  });
});
