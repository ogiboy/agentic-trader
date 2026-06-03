import { describe, expect, it } from 'vitest';

import {
  dashboardPages,
  dashboardStatusLine,
  dashboardTitle,
  formatPersona,
  getTuiCopy,
  getPageForShortcut,
  getPageLabel,
  normalizeTuiLocale,
  rotateInstructionMode,
  rotatePersona,
} from './copy.mjs';

describe('Ink TUI copy helpers', () => {
  it('keeps navigation labels and shortcuts in one catalog', () => {
    expect(dashboardTitle).toBe('AGENTIC TRADER // INK CONTROL ROOM');
    expect(dashboardPages).toEqual([
      'overview',
      'runtime',
      'portfolio',
      'review',
      'memory',
      'chat',
      'settings',
    ]);
    expect(getPageLabel('memory')).toBe('Decision Evidence');
    expect(getPageLabel('missing')).toBe('Unknown');
    expect(getPageForShortcut('5')).toBe('memory');
    expect(getPageForShortcut('8')).toBeUndefined();
  });

  it('formats shared persona and status copy', () => {
    expect(formatPersona('operator_liaison')).toBe('Operator Assistant');
    expect(formatPersona('custom')).toBe('custom');
    expect(formatPersona('')).toBe('-');
    expect(rotatePersona('operator_liaison', 1)).toBe('regime_analyst');
    expect(rotateInstructionMode('preview', -1)).toBe('apply');
    expect(dashboardStatusLine({ busy: true, page: 'review' })).toContain(
      'page 4/7: Review',
    );
    expect(dashboardStatusLine({ busy: true, page: 'review' })).toContain(
      'working...',
    );
  });

  it('supports Turkish copy through the shared UI locale env contract', () => {
    const tr = getTuiCopy('tr-TR');
    expect(normalizeTuiLocale('tr-TR')).toBe('tr');
    expect(tr.dashboardTitle).toBe('AGENTIC TRADER // INK KONTROL ODASI');
    expect(getPageLabel('overview', tr)).toBe('Genel Bakis');
    expect(formatPersona('portfolio_manager', tr)).toBe('Portfoy Yoneticisi');
    expect(dashboardStatusLine({ busy: true, page: 'settings', copy: tr }))
      .toContain('page 7/7: Ayarlar');
    expect(dashboardStatusLine({ busy: true, page: 'settings', copy: tr }))
      .toContain('calisiyor...');
  });
});
