import { describe, expect, it, vi } from 'vitest';

import
  {
    WebguiHttpError,
    canonicalLines,
    formatList,
    formatNumber,
    formatPercent,
    formatSourceHealthCount,
    formatTimestamp,
    marketContextLines,
    readJson,
    sourceHealthSummaryLine,
    tradeContextLines,
  } from './control-room';

describe('control-room formatting helpers', () => {
  it('formats primitive display values defensively', () => {
    expect(formatNumber(12.345)).toBe('12.35');
    expect(formatNumber('12')).toBe('-');
    expect(formatPercent(0.1234, 1)).toBe('12.3%');
    expect(formatPercent(Number.NaN)).toBe('-');
    expect(formatList(['AAPL', 'MSFT'])).toBe('AAPL, MSFT');
    expect(formatList([])).toBe('-');
    expect(formatSourceHealthCount({})).toBe('0');
    expect(
      sourceHealthSummaryLine({ fresh: 2, missing: '1', unknown: true }),
    ).toBe('fresh 2 / missing 1 / unknown true');
    expect(sourceHealthSummaryLine(undefined)).toBe('-');
    expect(formatTimestamp('not-a-date')).toBe('not-a-date');
    expect(formatTimestamp(null)).toBe('-');
  });

  it('builds dashboard evidence lines with placeholders', () => {
    expect(tradeContextLines(null)).toEqual([
      'No persisted trade context is available yet.',
    ]);
    expect(
      tradeContextLines({
        consensus: { alignment_level: 'strong' },
        execution_adapter: 'paper',
        execution_backend: 'simulated',
        execution_outcome_status: 'paper_filled',
        execution_rationale: 'risk ok',
        manager_rationale: 'setup ok',
        review_summary: 'valid',
        routed_models: { manager: 'qwen' },
        run_id: 'run-1',
        trade_id: 'trade-1',
      }),
    ).toContain('Routed Models: manager:qwen');

    expect(canonicalLines(null)).toEqual([
      'No canonical analysis snapshot is available yet.',
    ]);
    expect(
      canonicalLines({
        completeness_score: 0.9,
        disclosures: [1],
        fundamental: { attribution: { source_name: 'sec' } },
        macro: { attribution: { source_name: 'fred' } },
        market: { attribution: { source_name: 'alpaca' } },
        missing_sections: ['macro'],
        news_events: [1, 2],
        source_attributions: [
          {
            freshness: 'fresh',
            provider_type: 'market',
            source_name: 'alpaca',
            source_role: 'primary',
          },
        ],
        summary: 'ready',
      }),
    ).toContain('Source: market:alpaca (primary, fresh)');

    expect(marketContextLines(null)).toEqual([
      'No persisted market context pack is available yet.',
    ]);
    expect(
      marketContextLines({
        anomaly_flags: [],
        bars_analyzed: 10,
        bars_expected: 12,
        coverage_ratio: 0.83,
        data_quality_flags: ['short_window'],
        horizons: [{ horizon_bars: 5, max_drawdown_pct: -2, return_pct: 1 }],
        interval: '1d',
        lookback: '30d',
        summary: 'uptrend',
        window_end: '2026-05-02',
        window_start: '2026-04-01',
      }),
    ).toContain('5 bars | - | return=1 | drawdown=-2');
  });

  it('reads JSON with same-origin credentials and typed failures', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce({
      json: async () => ({ ok: true }),
      ok: true,
    });
    vi.stubGlobal('fetch', fetchMock);
    await expect(readJson('/api/dashboard')).resolves.toEqual({ ok: true });
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/dashboard',
      expect.objectContaining({
        cache: 'no-store',
        credentials: 'same-origin',
      }),
    );

    fetchMock.mockResolvedValueOnce({
      json: async () => ({ error: 'nope' }),
      ok: false,
      status: 401,
    });
    await expect(readJson('/api/dashboard')).rejects.toMatchObject({
      message: 'nope',
      name: 'WebguiHttpError',
      status: 401,
    } satisfies Partial<WebguiHttpError>);
    vi.unstubAllGlobals();
  });
});
