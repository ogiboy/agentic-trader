import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  getDashboardSnapshot,
  runInstruction,
} from '../../../lib/agentic-trader';
import { POST } from './route';

vi.mock('../../../lib/agentic-trader', () => ({
  getDashboardSnapshot: vi.fn(),
  runInstruction: vi.fn(),
}));

function instructionRequest(body: unknown): Request {
  return new Request('http://localhost:3210/api/instruct', {
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
  vi.mocked(getDashboardSnapshot).mockReset();
  vi.mocked(runInstruction).mockReset();
  delete process.env.AGENTIC_TRADER_WEBGUI_TOKEN;
});

describe('instruction route', () => {
  it('validates instruction shape before dispatch', async () => {
    process.env.AGENTIC_TRADER_WEBGUI_TOKEN = 'local-token';

    expect((await POST(instructionRequest({ message: '' }))).status).toBe(400);
    expect(
      (await POST(instructionRequest({ message: 'ok', apply: 'yes' }))).status,
    ).toBe(400);
    expect(
      (await POST(instructionRequest({ message: 'x'.repeat(6_001) }))).status,
    ).toBe(413);
  });

  it('returns instruction result with a fresh dashboard', async () => {
    process.env.AGENTIC_TRADER_WEBGUI_TOKEN = 'local-token';
    vi.mocked(runInstruction).mockResolvedValue({ applied: true });
    vi.mocked(getDashboardSnapshot).mockResolvedValue({
      status: { runtime_state: 'idle' },
    });

    const response = await POST(
      instructionRequest({ message: ' reduce risk ', apply: true }),
    );
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({
      dashboard: { status: { runtime_state: 'idle' } },
      result: { applied: true },
    });
    expect(vi.mocked(runInstruction)).toHaveBeenCalledWith('reduce risk', true);
  });
});
