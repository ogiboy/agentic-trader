// @vitest-environment jsdom

import { describe, expect, it, vi } from 'vitest';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';

import {
  ActiveView,
  ControlRoom,
  WebguiHttpError,
  canonicalLines,
  failedCheckNames,
  formatList,
  formatNumber,
  formatPercent,
  formatSourceHealthCount,
  formatTimestamp,
  localToolLines,
  marketContextLines,
  normalizeChatHistory,
  proposalLines,
  providerWarningLines,
  readJson,
  readinessLines,
  sourceHealthSummaryLine,
  systemStatusItems,
  tradeContextLines,
  unavailableSectionLines,
} from './control-room';

const dashboardFixture = {
  agentActivity: {
    recent_stage_events: [
      {
        created_at: '2026-05-10T00:00:00Z',
        message: 'Planner completed',
        stage: 'planner',
        status: 'ok',
      },
    ],
  },
  broker: {
    backend: 'paper',
    execution_mode: 'paper',
    external_paper: true,
    healthcheck: { message: 'healthy' },
    kill_switch_active: false,
    message: 'paper mode',
  },
  calendar: { session: { venue: 'NYSE' } },
  canonicalSnapshot: {
    snapshot: {
      completeness_score: 0.91,
      disclosures: [],
      fundamental: { attribution: { source_name: 'sec' } },
      macro: { attribution: { source_name: 'fred' } },
      market: { attribution: { source_name: 'alpaca' } },
      missing_sections: [],
      news_events: [{ title: 'fresh news' }],
      source_attributions: [],
      summary: 'fresh canonical context',
    },
  },
  chatHistory: {
    entries: [
      {
        persona: 'operator_liaison',
        response_text: 'Ready.',
        user_message: 'Status?',
      },
    ],
  },
  doctor: { model: 'qwen3:8b', runtime_mode: 'training' },
  financeOps: { accounting: { currency: 'USD' } },
  logs: [
    {
      created_at: '2026-05-10T00:00:00Z',
      event_type: 'cycle',
      level: 'info',
      message: 'cycle ok',
      symbol: 'AAPL',
    },
  ],
  marketContext: {
    contextPack: {
      anomaly_flags: [],
      bars_analyzed: 20,
      bars_expected: 20,
      coverage_ratio: 1,
      data_quality_flags: [],
      horizons: [{ horizon_bars: 5, max_drawdown_pct: -1, return_pct: 2 }],
      interval: '1d',
      lookback: '30d',
      summary: 'uptrend',
      window_end: '2026-05-10',
      window_start: '2026-04-10',
    },
  },
  memory: {
    matches: [
      {
        created_at: '2026-05-09T00:00:00Z',
        note: 'risk memory',
        score: 0.87,
        symbol: 'AAPL',
      },
    ],
  },
  modelService: {
    app_owned: true,
    base_url: 'http://127.0.0.1:11434',
    model_available: true,
    message: 'ready',
    service_reachable: true,
  },
  camofoxService: {
    app_owned: true,
    base_url: 'http://127.0.0.1:9222',
    message: 'ready',
  },
  webGui: { app_owned: true, message: 'ready', url: 'http://127.0.0.1:3210' },
  portfolio: {
    accounting: { cash: 1000, currency: 'USD', equity: 1100 },
    positions: [
      { market_value: 100, quantity: 1, symbol: 'AAPL', unrealized_pnl: 2 },
    ],
  },
  preferences: { currencies: ['USD'] },
  providerDiagnostics: {
    configured_keys: { alpaca: true, finnhub: false, fmp: true },
    market_data: { selected_provider: 'alpaca', selected_role: 'primary' },
    news: { mode: 'firecrawl' },
    warnings: ['fallback configured'],
  },
  research: {
    backend: 'firecrawl',
    cycleControl: {
      status: 'paused',
      trigger_now_requested: true,
    },
    latestDigestReplay: {
      available: true,
    },
    source_health_summary: { fresh: 2, missing: 0, unknown: 1 },
    status: 'ready',
  },
  review: {
    record: {
      manager_rationale: 'manager ok',
      review_summary: 'review ok',
      symbol: 'AAPL',
    },
  },
  status: {
    live_process: true,
    runtime_mode: 'training',
    runtime_state: 'running',
    state: {
      current_symbol: 'AAPL',
      cycle_count: 3,
      interval: '1d',
      pid: 42,
      stop_requested: false,
      updated_at: '2026-05-10T00:00:00Z',
    },
  },
  supervisor: { stderr_tail: ['no stderr'], stdout_tail: ['started'] },
  tradeContext: {
    record: {
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
    },
  },
  tradeProposals: {
    available: true,
    error: null,
    proposals: [
      {
        confidence: 0.82,
        notional: 250,
        proposal_id: 'proposal-1',
        reference_price: 190,
        side: 'buy',
        source: 'scanner',
        status: 'pending',
        stop_loss: 182,
        symbol: 'AAPL',
        take_profit: 205,
        thesis: 'Momentum continuation with manual review.',
      },
    ],
  },
  v1Readiness: {
    alpaca_paper: { checks: [{ name: 'keys', passed: true }], ready: true },
    paper_operations: {
      allowed: true,
      checks: [{ name: 'data', passed: true }],
    },
  },
};

function renderActiveView(
  tab: Parameters<typeof ActiveView>[0]['tab'],
  dashboard: typeof dashboardFixture | Record<string, unknown> = dashboardFixture,
) {
  return renderToStaticMarkup(
    React.createElement(ActiveView, {
      busy: null,
      chatDraft: 'hello',
      chatHistory: normalizeChatHistory(dashboard),
      chatPersona: 'operator_liaison',
      currentCycle: [['Symbol', 'AAPL']],
      dashboard,
      instructionDraft: 'reduce risk',
      instructionMode: 'preview',
      instructionResult: { ok: true },
      onChatDraftChange: vi.fn(),
      onChatPersonaChange: vi.fn(),
      onInstructionDraftChange: vi.fn(),
      onInstructionModeChange: vi.fn(),
      onSendChat: vi.fn(),
      onSendInstruction: vi.fn(),
      onProposalAction: vi.fn(),
      onProposalNoteChange: vi.fn(),
      onToolAction: vi.fn(),
      proposalNote: 'desk review',
      system: [['Runtime', 'training']],
      tab,
    }),
  );
}

function jsonResponse(
  payload: unknown,
  options: { ok?: boolean; status?: number } = {},
) {
  return {
    json: async () => payload,
    ok: options.ok ?? true,
    status: options.status ?? 200,
  };
}

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
    ).toContain('5 bars | undefined | return=1 | drawdown=-2');
  });

  it('normalizes availability, readiness, provider, and chat summaries', () => {
    expect(unavailableSectionLines({ available: false }, 'Review')).toEqual([
      'Review unavailable: Unknown error.',
    ]);
    expect(unavailableSectionLines({ available: true }, 'Review')).toBeNull();
    expect(
      normalizeChatHistory({
        chatHistory: {
          entries: [
            {
              persona: 'operator_liaison',
              response_text: 'a',
              user_message: 'u1',
            },
            { persona: 'risk_manager', response_text: 'b', user_message: 'u2' },
          ],
        },
      }),
    ).toEqual([
      { persona: 'risk_manager', response: 'b', user: 'u2' },
      { persona: 'operator_liaison', response: 'a', user: 'u1' },
    ]);
    expect(
      failedCheckNames({
        checks: [
          { blocking: true, name: 'market data', passed: false },
          { blocking: false, name: 'optional', passed: false },
          { blocking: true, name: 'broker', passed: false },
        ],
      }),
    ).toBe('market data, broker');
    expect(readinessLines({ broker: {}, v1Readiness: {} })).toContain(
      'Can run local paper cycle: no',
    );
    expect(providerWarningLines({ providerDiagnostics: {} })).toContain(
      'No provider warnings.',
    );
    expect(systemStatusItems(dashboardFixture)).toContainEqual([
      'Base URL',
      'http://127.0.0.1:11434/v1',
    ]);
    expect(systemStatusItems(dashboardFixture)).toContainEqual([
      'Ollama Reachable',
      'yes',
    ]);
    expect(localToolLines(dashboardFixture)).toContain('Model Adapter: ollama');
    expect(localToolLines(dashboardFixture)).toContain(
      'Firecrawl Runtime: internal SDK first; host CLI fallback disabled by ownership',
    );
    expect(proposalLines(dashboardFixture)).toContain(
      'proposal-1 | AAPL BUY | pending | $250.00 | confidence=0.82 | source=scanner',
    );
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

  it('renders every active tab from a dashboard payload', () => {
    for (const tab of [
      'overview',
      'runtime',
      'portfolio',
      'proposals',
      'review',
      'memory',
      'chat',
      'settings',
    ] as const) {
      expect(renderActiveView(tab)).toContain('panel');
    }
    expect(renderActiveView('overview')).toContain('Agentic Trader Web GUI');
    expect(renderActiveView('runtime')).toContain('Runtime State');
    expect(renderActiveView('portfolio')).toContain('Portfolio');
    expect(renderActiveView('proposals')).toContain('Proposal Desk');
    expect(renderActiveView('review')).toContain('Latest Review');
    expect(renderActiveView('memory')).toContain('Similar Past Runs');
    expect(renderActiveView('chat')).toContain('Operator Chat');
    expect(renderActiveView('settings')).toContain('Operator Instruction');
  });

  it('renders sparse dashboard fallbacks across active tabs', () => {
    const sparseDashboard = {
      broker: {},
      calendar: {},
      financeOps: {},
      logs: [],
      marketContext: {},
      portfolio: { available: false, error: 'portfolio locked' },
      providerDiagnostics: {},
      review: { available: false, error: 'review locked' },
      riskReport: { available: false, error: 'risk locked' },
      status: { live_process: false, runtime_state: 'idle', state: {} },
      tradeProposals: {
        available: false,
        error: 'proposal locked',
        proposals: [],
      },
      v1Readiness: {
        alpaca_paper: { checks: [], ready: false },
        paper_operations: { allowed: false, checks: [] },
      },
    };

    expect(renderActiveView('overview', sparseDashboard)).toContain(
      'No live agent stage events yet.',
    );
    expect(renderActiveView('runtime', sparseDashboard)).toContain(
      'No runtime events recorded yet.',
    );
    expect(renderActiveView('portfolio', sparseDashboard)).toContain(
      'Portfolio unavailable: portfolio locked',
    );
    expect(renderActiveView('proposals', sparseDashboard)).toContain(
      'Proposal desk unavailable: proposal locked',
    );
    expect(renderActiveView('review', sparseDashboard)).toContain(
      'Latest review unavailable: review locked',
    );
    expect(renderActiveView('memory', sparseDashboard)).toContain(
      'No similar historical memories found yet.',
    );
    expect(renderActiveView('chat', sparseDashboard)).toContain(
      'No chat messages yet.',
    );
    expect(renderActiveView('settings', sparseDashboard)).toContain(
      'No recent runs recorded yet.',
    );
  });

  it('loads the control room and exercises runtime, chat, and instruction actions', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(dashboardFixture))
      .mockResolvedValueOnce(jsonResponse(dashboardFixture))
      .mockResolvedValueOnce(
        jsonResponse({
          dashboard: dashboardFixture,
          message: 'Strict one-shot cycle completed.',
        }),
      )
      .mockResolvedValueOnce(jsonResponse({ response: 'chat ok' }))
      .mockResolvedValueOnce(jsonResponse(dashboardFixture))
      .mockResolvedValueOnce(
        jsonResponse({
          dashboard: dashboardFixture,
          result: {
            applied: true,
            instruction: {
              rationale: 'safer',
              requires_confirmation: false,
              should_update_preferences: true,
              summary: 'reduce risk',
            },
          },
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          dashboard: {
            ...dashboardFixture,
            tradeProposals: { available: true, proposals: [] },
          },
          message: 'AAPL proposal rejected.',
        }),
      );
    vi.stubGlobal('fetch', fetchMock);

    render(React.createElement(ControlRoom));
    await screen.findByText('Agentic Trader Web GUI');

    fireEvent.click(screen.getByRole('button', { name: 'Refresh' }));
    await screen.findByText('Dashboard refreshed.');

    fireEvent.click(screen.getByRole('button', { name: 'One Shot' }));
    await screen.findByText('Strict one-shot cycle completed.');

    fireEvent.click(screen.getByRole('button', { name: 'Chat' }));
    fireEvent.change(screen.getByLabelText('Role'), {
      target: { value: 'risk_steward' },
    });
    fireEvent.change(
      screen.getByPlaceholderText('Ask for a review, status, or explanation.'),
      { target: { value: 'Explain current risk' } },
    );
    fireEvent.click(screen.getByRole('button', { name: 'Send' }));
    await screen.findByText('Operator reply received.');

    fireEvent.click(screen.getByRole('button', { name: 'Settings' }));
    fireEvent.change(screen.getByLabelText('Mode'), {
      target: { value: 'apply' },
    });
    fireEvent.change(
      screen.getByPlaceholderText(
        'Make the system more conservative and protective.',
      ),
      { target: { value: 'Reduce risk' } },
    );
    fireEvent.click(screen.getByRole('button', { name: 'Apply' }));
    await screen.findByText('Preferences updated from operator instruction.');

    fireEvent.click(screen.getByRole('button', { name: 'Proposals' }));
    fireEvent.change(
      screen.getByPlaceholderText('Approval note or rejection reason.'),
      { target: { value: 'spread widened' } },
    );
    fireEvent.click(screen.getByRole('button', { name: 'Reject' }));
    await screen.findByText('AAPL proposal rejected.');

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(7));
    vi.unstubAllGlobals();
  });

  it('prompts for and unlocks a protected Web GUI session', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse({ error: 'token required' }, { ok: false, status: 401 }),
      )
      .mockResolvedValueOnce(jsonResponse({ authenticated: true }))
      .mockResolvedValueOnce(jsonResponse(dashboardFixture));
    vi.stubGlobal('fetch', fetchMock);

    render(React.createElement(ControlRoom));
    const tokenInput = await screen.findByLabelText('Web GUI token');
    fireEvent.change(tokenInput, { target: { value: 'local-token' } });
    await act(async () => {
      fireEvent.submit(tokenInput.closest('form') as HTMLFormElement);
    });

    await screen.findByText('Agentic Trader Web GUI');
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
    vi.unstubAllGlobals();
  });

  it('renders the initial control room shell while loading', () => {
    const html = renderToStaticMarkup(React.createElement(ControlRoom));
    expect(html).toContain('Agentic Trader');
    expect(html).toContain('Loading dashboard');
    expect(html).toContain('Local-first control room');
  });
});
