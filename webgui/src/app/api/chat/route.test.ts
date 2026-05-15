import { afterEach, describe, expect, it, vi } from 'vitest';

import { runChat } from '../../../lib/agentic-trader';
import { POST } from './route';

vi.mock('../../../lib/agentic-trader', () => ({
  runChat: vi.fn(),
}));

function chatRequest(body: unknown): Request {
  return new Request('http://localhost:3210/api/chat', {
    method: 'POST',
    headers: {
      origin: 'http://localhost:3210',
      'content-type': 'application/json',
      'x-agentic-trader-token': 'local-token',
    },
    body: JSON.stringify(body),
  });
}

afterEach(() => {
  vi.useRealTimers();
  vi.mocked(runChat).mockReset();
  delete process.env.AGENTIC_TRADER_WEBGUI_TOKEN;
});

describe('chat route', () => {
  it('validates message and persona inputs', async () => {
    process.env.AGENTIC_TRADER_WEBGUI_TOKEN = 'local-token';

    expect((await POST(chatRequest({ message: '' }))).status).toBe(400);
    expect(
      (await POST(chatRequest({ message: 'x'.repeat(6_001) }))).status,
    ).toBe(413);
    const badPersona = await POST(
      chatRequest({ message: 'hello', persona: 'unknown' }),
    );
    expect(badPersona.status).toBe(400);
  });

  it('runs chat with the default persona and redacts failures', async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-05-10T00:00:00Z'));
    process.env.AGENTIC_TRADER_WEBGUI_TOKEN = 'local-token';
    vi.mocked(runChat).mockResolvedValueOnce({ response: 'ready' });

    const response = await POST(chatRequest({ message: ' hello ' }));
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ response: 'ready' });
    expect(vi.mocked(runChat)).toHaveBeenCalledWith(
      'operator_liaison',
      'hello',
    );

    vi.advanceTimersByTime(1_500);
    vi.mocked(runChat).mockRejectedValueOnce(new Error('API_KEY=secret'));
    const failed = await POST(chatRequest({ message: 'again' }));
    expect(failed.status).toBe(500);
    expect(await failed.json()).toEqual({ error: 'API_KEY=<redacted>' });
  });
});
