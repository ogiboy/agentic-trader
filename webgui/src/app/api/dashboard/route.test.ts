import { afterEach, describe, expect, it, vi } from 'vitest';

import { getDashboardSnapshot } from '../../../lib/agentic-trader';
import { GET } from './route';

vi.mock('../../../lib/agentic-trader', () => ({
  getDashboardSnapshot: vi.fn(),
}));

function dashboardRequest(headers: HeadersInit = {}): Request {
  return new Request('http://localhost:3210/api/dashboard', {
    headers: {
      origin: 'http://localhost:3210',
      'x-agentic-trader-token': 'local-token',
      ...headers,
    },
  });
}

afterEach(() => {
  vi.mocked(getDashboardSnapshot).mockReset();
  delete process.env.AGENTIC_TRADER_WEBGUI_TOKEN;
});

describe('dashboard route', () => {
  it('returns snapshots for authorized browser requests', async () => {
    process.env.AGENTIC_TRADER_WEBGUI_TOKEN = 'local-token';
    vi.mocked(getDashboardSnapshot).mockResolvedValue({
      status: { runtime_state: 'idle' },
    });

    const response = await GET(dashboardRequest());
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({
      status: { runtime_state: 'idle' },
    });
  });

  it('rejects unauthorized requests and redacts snapshot failures', async () => {
    process.env.AGENTIC_TRADER_WEBGUI_TOKEN = 'local-token';

    expect(
      (await GET(new Request('http://localhost:3210/api/dashboard'))).status,
    ).toBe(401);

    vi.mocked(getDashboardSnapshot).mockRejectedValueOnce(
      new Error('PASSWORD=secret failed'),
    );
    const failed = await GET(dashboardRequest());
    expect(failed.status).toBe(500);
    expect(await failed.json()).toEqual({
      error: 'PASSWORD=<redacted> failed',
    });
  });
});
