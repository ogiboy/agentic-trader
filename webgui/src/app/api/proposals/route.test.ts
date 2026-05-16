import { afterEach, describe, expect, it, vi } from 'vitest';

import { runProposalAction } from '../../../lib/agentic-trader';
import { POST } from './route';

vi.mock('../../../lib/agentic-trader', () => ({
  runProposalAction: vi.fn(),
}));

function proposalRequest(body: unknown, headers: HeadersInit = {}): Request {
  return new Request('http://localhost:3210/api/proposals', {
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
  vi.mocked(runProposalAction).mockReset();
  delete process.env.AGENTIC_TRADER_WEBGUI_TOKEN;
});

describe('proposals route', () => {
  it('rejects unauthenticated and invalid proposal actions', async () => {
    process.env.AGENTIC_TRADER_WEBGUI_TOKEN = 'local-token';

    const unauthorized = await POST(
      new Request('http://localhost:3210/api/proposals', {
        method: 'POST',
        headers: {
          origin: 'http://localhost:3210',
          'content-type': 'application/json',
        },
        body: JSON.stringify({ kind: 'approve', proposalId: 'proposal-1' }),
      }),
    );
    expect(unauthorized.status).toBe(401);

    const invalid = await POST(
      proposalRequest({ kind: 'live-submit', proposalId: 'proposal-1' }),
    );
    expect(invalid.status).toBe(400);
    expect(await invalid.json()).toEqual({ error: 'invalid proposal action' });

    const missingId = await POST(proposalRequest({ kind: 'reject' }));
    expect(missingId.status).toBe(400);
    expect(await missingId.json()).toEqual({ error: 'proposal id is required' });
  });

  it('runs supported manual-review actions through the allowlist', async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-05-10T00:00:00Z'));
    process.env.AGENTIC_TRADER_WEBGUI_TOKEN = 'local-token';
    vi.mocked(runProposalAction).mockResolvedValue({
      dashboard: { tradeProposals: { proposals: [] } },
      message: 'approved',
      result: { proposal: { status: 'executed' } },
    });

    const first = await POST(
      proposalRequest({
        kind: 'approve',
        proposalId: 'proposal-1',
        reviewNotes: 'desk approved',
      }),
    );
    expect(first.status).toBe(200);
    expect(await first.json()).toEqual({
      dashboard: { tradeProposals: { proposals: [] } },
      message: 'approved',
      result: { proposal: { status: 'executed' } },
    });
    vi.advanceTimersByTime(3_000);

    const second = await POST(
      proposalRequest({
        kind: 'reject',
        proposalId: 'proposal-2',
        reviewNotes: 'spread too wide',
      }),
    );
    expect(second.status).toBe(200);
    expect(vi.mocked(runProposalAction)).toHaveBeenCalledWith(
      'approve',
      'proposal-1',
      'desk approved',
    );
    expect(vi.mocked(runProposalAction)).toHaveBeenCalledWith(
      'reject',
      'proposal-2',
      'spread too wide',
    );
  });

  it('redacts thrown proposal errors', async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-05-10T01:00:00Z'));
    process.env.AGENTIC_TRADER_WEBGUI_TOKEN = 'local-token';
    vi.mocked(runProposalAction).mockRejectedValue(
      new Error('BROKER_TOKEN=secret-value failed'),
    );

    const response = await POST(
      proposalRequest({ kind: 'approve', proposalId: 'proposal-1' }),
    );
    expect(response.status).toBe(500);
    expect(await response.json()).toEqual({
      error: 'BROKER_TOKEN=<redacted> failed',
    });
  });
});
