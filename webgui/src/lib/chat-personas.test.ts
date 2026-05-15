import { describe, expect, it } from 'vitest';

import { CHAT_PERSONAS, formatChatPersona, isChatPersona } from './chat-personas';

describe('chat persona formatting', () => {
  it('recognizes known personas and preserves primitive fallbacks', () => {
    for (const persona of CHAT_PERSONAS) {
      expect(isChatPersona(persona)).toBe(true);
      expect(formatChatPersona(persona)).not.toBe('-');
    }

    expect(isChatPersona('unknown')).toBe(false);
    expect(isChatPersona(42)).toBe(false);
    expect(formatChatPersona('')).toBe('-');
    expect(formatChatPersona('custom')).toBe('custom');
    expect(formatChatPersona(7)).toBe('7');
    expect(formatChatPersona(false)).toBe('false');
    expect(formatChatPersona({})).toBe('-');
  });
});
