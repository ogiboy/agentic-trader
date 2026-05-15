import { afterEach, describe, expect, it, vi } from 'vitest';

import { runRuntimeAction } from '../../../lib/agentic-trader';
import { POST } from './route';

vi.mock('../../../lib/agentic-trader', () => ({
  runRuntimeAction: vi.fn(),
}));

function runtimeRequest(body: unknown, headers: HeadersInit = {}): Request {
  return new Request('http://localhost:3210/api/runtime', {
    method: 'POST',
    headers: {
      origin: 'http://localhost:3210',
      'content-type': 'application/json',
      'x-agentic-trader-token': 'local-token',
      ...headers,
    },
    body: JSON.stringify(body),
  });
}

afterEach(() => {
  vi.useRealTimers();
  vi.mocked(runRuntimeAction).mockReset();
  delete process.env.AGENTIC_TRADER_WEBGUI_TOKEN;
});

describe('runtime route', () => {
  it('rejects unauthenticated and invalid runtime actions', async () => {
    process.env.AGENTIC_TRADER_WEBGUI_TOKEN = 'local-token';

    const unauthorized = await POST(
      new Request('http://localhost:3210/api/runtime', {
        method: 'POST',
        headers: {
          origin: 'http://localhost:3210',
          'content-type': 'application/json',
        },
        body: JSON.stringify({ kind: 'start' }),
      }),
    );
    expect(unauthorized.status).toBe(401);

    const invalid = await POST(runtimeRequest({ kind: 'trade-live-now' }));
    expect(invalid.status).toBe(400);
    expect(await invalid.json()).toEqual({ error: 'invalid runtime action' });
  });

  it('runs supported actions and releases the single-flight guard', async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-05-10T00:00:00Z'));
    process.env.AGENTIC_TRADER_WEBGUI_TOKEN = 'local-token';
    vi.mocked(runRuntimeAction).mockResolvedValue({
      dashboard: { status: { runtime_state: 'idle' } },
      message: 'started',
    });

    const first = await POST(runtimeRequest({ kind: 'start' }));
    expect(first.status).toBe(200);
    expect(await first.json()).toEqual({
      dashboard: { status: { runtime_state: 'idle' } },
      message: 'started',
    });
    vi.advanceTimersByTime(5_000);

    const second = await POST(runtimeRequest({ kind: 'stop' }));
    expect(second.status).toBe(200);
    expect(vi.mocked(runRuntimeAction)).toHaveBeenCalledWith('start');
    expect(vi.mocked(runRuntimeAction)).toHaveBeenCalledWith('stop');
  });

  it('redacts thrown runtime errors', async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-05-10T01:00:00Z'));
    process.env.AGENTIC_TRADER_WEBGUI_TOKEN = 'local-token';
    vi.mocked(runRuntimeAction).mockRejectedValue(
      new Error('TOKEN=secret-value backend failed'),
    );

    const response = await POST(runtimeRequest({ kind: 'one-shot' }));
    expect(response.status).toBe(500);
    expect(await response.json()).toEqual({
      error: 'TOKEN=<redacted> backend failed',
    });
  });
});
