import { afterEach, describe, expect, it, vi } from 'vitest';

import { runToolAction } from '../../../lib/agentic-trader';
import { POST } from './route';

vi.mock('../../../lib/agentic-trader', () => ({
  runToolAction: vi.fn(),
}));

function toolRequest(body: unknown, headers: HeadersInit = {}): Request {
  return new Request('http://localhost:3210/api/tools', {
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
  vi.mocked(runToolAction).mockReset();
  delete process.env.AGENTIC_TRADER_WEBGUI_TOKEN;
});

describe('tools route', () => {
  it('rejects unauthenticated and invalid tool actions', async () => {
    process.env.AGENTIC_TRADER_WEBGUI_TOKEN = 'local-token';

    const unauthorized = await POST(
      new Request('http://localhost:3210/api/tools', {
        method: 'POST',
        headers: {
          origin: 'http://localhost:3210',
          'content-type': 'application/json',
        },
        body: JSON.stringify({ kind: 'enable-local-tools' }),
      }),
    );
    expect(unauthorized.status).toBe(401);

    const invalid = await POST(toolRequest({ kind: 'generate-secret' }));
    expect(invalid.status).toBe(400);
    expect(await invalid.json()).toEqual({ error: 'invalid tool action' });
  });

  it('runs supported local tool actions through the allowlist', async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-05-10T00:00:00Z'));
    process.env.AGENTIC_TRADER_WEBGUI_TOKEN = 'local-token';
    vi.mocked(runToolAction).mockResolvedValue({
      dashboard: { modelService: { app_owned: true } },
      message: 'started',
    });

    const first = await POST(toolRequest({ kind: 'start-model-service' }));
    expect(first.status).toBe(200);
    expect(await first.json()).toEqual({
      dashboard: { modelService: { app_owned: true } },
      message: 'started',
    });
    vi.advanceTimersByTime(5_000);

    const second = await POST(toolRequest({ kind: 'enable-local-tools' }));
    expect(second.status).toBe(200);
    expect(vi.mocked(runToolAction)).toHaveBeenCalledWith('start-model-service');
    expect(vi.mocked(runToolAction)).toHaveBeenCalledWith('enable-local-tools');
  });

  it('redacts thrown tool errors', async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-05-10T01:00:00Z'));
    process.env.AGENTIC_TRADER_WEBGUI_TOKEN = 'local-token';
    vi.mocked(runToolAction).mockRejectedValue(
      new Error('CAMOFOX_ACCESS_KEY=secret-value failed'),
    );

    const response = await POST(toolRequest({ kind: 'start-camofox-service' }));
    expect(response.status).toBe(500);
    expect(await response.json()).toEqual({
      error: 'CAMOFOX_ACCESS_KEY=<redacted> failed',
    });
  });
});
