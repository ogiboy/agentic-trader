import { beforeEach, describe, expect, it, vi } from 'vitest';

const execFileMock = vi.hoisted(() => vi.fn());

vi.mock('node:child_process', () => ({
  execFile: execFileMock,
}));

function execSuccess(stdout: string) {
  execFileMock.mockImplementationOnce((_command, _args, _options, callback) => {
    callback(null, { stderr: '', stdout });
  });
}

function execFailure(error: NodeJS.ErrnoException & { stderr?: string }) {
  execFileMock.mockImplementationOnce((_command, _args, _options, callback) => {
    callback(error);
  });
}

describe('agentic-trader webgui CLI bridge', () => {
  beforeEach(() => {
    execFileMock.mockReset();
    process.env.AGENTIC_TRADER_PYTHON = '/usr/bin/python-test';
  });

  it('executes JSON commands through the configured Python module runner', async () => {
    const { execTrader } = await import('./agentic-trader');
    execSuccess('{"status":"ok"}');

    await expect(
      execTrader(['dashboard-snapshot'], { expectJson: true }),
    ).resolves.toEqual({
      status: 'ok',
    });
    expect(execFileMock).toHaveBeenCalledWith(
      '/usr/bin/python-test',
      ['-m', 'agentic_trader.cli', 'dashboard-snapshot'],
      expect.objectContaining({ maxBuffer: 8 * 1024 * 1024 }),
      expect.any(Function),
    );
  });

  it('falls back past missing executables and redacts command failures', async () => {
    const { execTrader } = await import('./agentic-trader');
    const missing = Object.assign(new Error('missing'), { code: 'ENOENT' });
    execFailure(missing);
    execSuccess('plain output');
    await expect(execTrader(['status'])).resolves.toEqual({
      stderr: '',
      stdout: 'plain output',
    });

    execFailure(
      Object.assign(new Error('failed'), {
        code: 'EFAIL',
        stderr: 'API_KEY=secret failed',
      }),
    );
    await expect(execTrader(['status'])).rejects.toThrow(
      'API_KEY=<redacted> failed',
    );
  });

  it('starts, stops, restarts, and one-shot runs from dashboard state', async () => {
    const { runRuntimeAction } = await import('./agentic-trader');
    execSuccess(
      JSON.stringify({
        preferences: { regions: ['US'] },
        status: { live_process: false, state: { interval: '1h' } },
      }),
    );
    execSuccess('');
    execSuccess(JSON.stringify({ status: { runtime_state: 'running' } }));

    await expect(runRuntimeAction('start')).resolves.toMatchObject({
      message: 'Background runtime launch requested for AAPL,MSFT (1h, 180d).',
    });
    expect(execFileMock.mock.calls[1][1]).toContain('launch');
    expect(execFileMock.mock.calls[1][1]).toContain('--continuous');

    execSuccess(
      JSON.stringify({
        status: { live_process: true, state: { pid: 42 } },
      }),
    );
    execSuccess('');
    execSuccess(JSON.stringify({ status: { runtime_state: 'idle' } }));
    await expect(runRuntimeAction('stop')).resolves.toMatchObject({
      message: 'Stop requested for PID 42.',
    });

    execSuccess(JSON.stringify({ status: { state: { symbols: ['AAPL'] } } }));
    execSuccess('');
    execSuccess(JSON.stringify({ status: { runtime_state: 'running' } }));
    await expect(runRuntimeAction('restart')).resolves.toMatchObject({
      message: 'Background runtime restart requested.',
    });

    execSuccess(
      JSON.stringify({
        marketContext: { contextPack: { interval: '1d', lookback: '30d' } },
        review: { record: { symbol: 'MSFT' } },
        status: { live_process: false, state: {} },
      }),
    );
    execSuccess('');
    execSuccess(JSON.stringify({ status: { runtime_state: 'idle' } }));
    await expect(runRuntimeAction('one-shot')).resolves.toMatchObject({
      message: 'Strict one-shot cycle completed for MSFT (1d, 30d).',
    });
  });

  it('returns guarded messages for already-running or unsupported actions', async () => {
    const { runRuntimeAction } = await import('./agentic-trader');
    execSuccess(
      JSON.stringify({
        status: { live_process: true, state: { pid: 99 } },
      }),
    );
    await expect(runRuntimeAction('start')).resolves.toMatchObject({
      message: 'Runtime already active with PID 99.',
    });

    execSuccess(JSON.stringify({ status: { live_process: false, state: {} } }));
    await expect(runRuntimeAction('stop')).resolves.toMatchObject({
      message: 'No managed runtime is currently active.',
    });

    execSuccess(JSON.stringify({ status: { state: { symbols: [] } } }));
    await expect(runRuntimeAction('restart')).resolves.toMatchObject({
      message: 'No saved runtime launch config is available yet.',
    });

    execSuccess(JSON.stringify({ status: { state: {} } }));
    await expect(runRuntimeAction('unsupported')).rejects.toThrow(
      'Unsupported runtime action',
    );
  });

  it('runs app-owned local tool actions through explicit CLI contracts', async () => {
    const { runToolAction } = await import('./agentic-trader');
    execSuccess(
      JSON.stringify({
        doctor: { model: 'qwen3:8b' },
        modelService: { configured_model: 'qwen3:8b' },
      }),
    );
    execSuccess(JSON.stringify({}));
    execSuccess(JSON.stringify({ model_available: true }));
    execSuccess(JSON.stringify({ modelService: { app_owned: true } }));

    await expect(runToolAction('start-model-service')).resolves.toMatchObject({
      message: 'App-owned model-service started; qwen3:8b is listed.',
    });
    expect(execFileMock.mock.calls[1][1]).toContain('tool-ownership');
    expect(execFileMock.mock.calls[2][1]).toContain('model-service');
    expect(execFileMock.mock.calls[2][1]).toContain('start');

    execSuccess(JSON.stringify({}));
    execSuccess(JSON.stringify({}));
    execSuccess(JSON.stringify({}));
    await expect(runToolAction('enable-local-tools')).resolves.toMatchObject({
      message: 'Local tool ownership set to app-owned.',
    });
    expect(execFileMock.mock.calls.at(-2)?.[1]).toContain('--firecrawl-owner');
    expect(execFileMock.mock.calls.at(-2)?.[1]).toContain('app-owned');

    execSuccess(JSON.stringify({}));
    execSuccess(JSON.stringify({}));
    execSuccess(JSON.stringify({}));
    await expect(runToolAction('enable-host-fallbacks')).resolves.toMatchObject({
      message: 'Host-managed fallback ownership enabled.',
    });
    expect(execFileMock.mock.calls.at(-2)?.[1]).toContain('--ollama-owner');
    expect(execFileMock.mock.calls.at(-2)?.[1]).toContain('host-owned');

    execSuccess(JSON.stringify({}));
    execSuccess(JSON.stringify({}));
    execSuccess(JSON.stringify({}));
    execSuccess(JSON.stringify({}));
    await expect(runToolAction('start-camofox-service')).resolves.toMatchObject({
      message: 'App-owned Camofox helper started.',
    });
    expect(execFileMock.mock.calls.at(-2)?.[1]).toContain('camofox-service');
  });

  it('runs proposal actions through explicit manual-review CLI contracts', async () => {
    const { runProposalAction } = await import('./agentic-trader');

    execSuccess(
      JSON.stringify({
        outcome: { status: 'filled' },
        proposal: { status: 'executed', symbol: 'AAPL' },
      }),
    );
    execSuccess(JSON.stringify({ tradeProposals: { proposals: [] } }));
    await expect(
      runProposalAction('approve', 'proposal-1', 'desk approved'),
    ).resolves.toMatchObject({
      message: 'AAPL proposal approved; proposal=executed, broker=filled.',
    });
    expect(execFileMock.mock.calls[0][1]).toEqual([
      '-m',
      'agentic_trader.cli',
      'proposal-approve',
      'proposal-1',
      '--review-notes',
      'desk approved',
      '--json',
    ]);

    execSuccess(JSON.stringify({ status: 'rejected', symbol: 'MSFT' }));
    execSuccess(JSON.stringify({ tradeProposals: { proposals: [] } }));
    await expect(
      runProposalAction('reject', 'proposal-2', 'spread too wide'),
    ).resolves.toMatchObject({
      message: 'MSFT proposal rejected.',
    });
    expect(execFileMock.mock.calls[2][1]).toContain('proposal-reject');
    expect(execFileMock.mock.calls[2][1]).toContain('--reason');

    execSuccess(
      JSON.stringify({ proposal: { status: 'executed', symbol: 'NVDA' } }),
    );
    execSuccess(JSON.stringify({ tradeProposals: { proposals: [] } }));
    await expect(
      runProposalAction('reconcile', 'proposal-3'),
    ).resolves.toMatchObject({
      message: 'NVDA proposal reconciled; status=executed.',
    });
    expect(execFileMock.mock.calls[4][1]).toContain('proposal-reconcile');

    await expect(runProposalAction('reject', 'proposal-4')).rejects.toThrow(
      'Rejection reason is required.',
    );
  });
});
