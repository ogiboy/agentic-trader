// @vitest-environment jsdom

import
  {
    act,
    cleanup,
    fireEvent,
    render,
    screen,
    waitFor,
  } from '@testing-library/react';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ControlRoomIntlProvider } from '@/i18n/ControlRoomIntlProvider';
import
  {
    ActiveView,
    ControlRoom,
    failedCheckNames,
    localToolActionLines,
    localToolLines,
    normalizeChatHistory,
    positionPlanCoverageLines,
    proposalLines,
    providerWarningLines,
    readinessLines,
    sourceHealthSummaryLine,
    systemStatusItems,
    unavailableSectionLines,
  } from './ControlRoom';
import { getControlRoomCopy } from './control-room/labels';

function withIntl(children: React.ReactNode) {
  return React.createElement(
    ControlRoomIntlProvider,
    { initialLocale: 'en' },
    children,
  );
}

if (!globalThis.Element.prototype.hasPointerCapture) {
  globalThis.Element.prototype.hasPointerCapture = () => false;
}

if (!globalThis.Element.prototype.scrollIntoView) {
  globalThis.Element.prototype.scrollIntoView = () => undefined;
}

async function chooseSelectOption(label: string, option: string) {
  fireEvent.pointerDown(screen.getByRole('combobox', { name: label }), {
    button: 0,
    ctrlKey: false,
    pointerId: 1,
    pointerType: 'mouse',
  });
  fireEvent.click(await screen.findByRole('option', { name: option }));
}

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
  financeOps: {
    accounting: { currency: 'USD' },
    positionPlanCoverage: {
      available: true,
      coverage_ratio: 0.5,
      missing_symbols: ['MSFT'],
      open_symbols: ['AAPL', 'MSFT'],
      planned_symbols: ['AAPL'],
    },
  },
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

afterEach(() => {
  cleanup();
  globalThis.localStorage?.clear?.();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

function renderActiveView(
  tab: Parameters<typeof ActiveView>[0]['tab'],
  dashboard:
    | typeof dashboardFixture
    | Record<string, unknown> = dashboardFixture,
) {
  return renderToStaticMarkup(
    withIntl(
      React.createElement(ActiveView, {
        busy: null,
        chatDraft: 'hello',
        chatHistory: normalizeChatHistory(dashboard),
        chatPersona: 'operator_liaison',
        currentCycle: [['Symbol', 'AAPL']],
        dashboard,
        diagnosticsCopy: getControlRoomCopy('en').diagnostics,
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
    ),
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
    const trCopy = getControlRoomCopy('tr');
    expect(readinessLines({ broker: {}, v1Readiness: {} }, trCopy)).toContain(
      'Yerel paper döngüsü çalışabilir: hayır',
    );
    expect(providerWarningLines({ providerDiagnostics: {} }, trCopy)).toContain(
      'Sağlayıcı uyarısı yok.',
    );
    expect(
      sourceHealthSummaryLine(
        { fresh: 2, missing: '1', unknown: true },
        trCopy,
      ),
    ).toBe('güncel 2 / eksik 1 / bilinmeyen true');
    expect(systemStatusItems(dashboardFixture, trCopy)).toContainEqual([
      'Temel URL',
      'http://127.0.0.1:11434/v1',
    ]);
    expect(systemStatusItems(dashboardFixture, trCopy)).toContainEqual([
      'Ollama Erişilebilir',
      'evet',
    ]);
    expect(localToolLines(dashboardFixture, trCopy)).toContain(
      'Model Adaptörü: ollama',
    );
    expect(localToolLines(dashboardFixture, trCopy)).toContain(
      'Firecrawl Çalışma Biçimi: önce dahili SDK; gerekirse host CLI yedeği sahiplik seçimi nedeniyle kapalı',
    );
    expect(
      localToolActionLines({
        ...dashboardFixture,
        camofoxService: {
          app_owned: true,
          message: 'not running',
          service_reachable: false,
        },
        modelService: {
          app_owned: true,
          configured_model: 'qwen3:8b',
          message: 'offline',
          model_available: false,
          service_reachable: false,
        },
        toolOwnership: {
          decisions_by_tool: {
            camofox: { mode: 'app-owned' },
            ollama: { mode: 'app-owned' },
          },
        },
      }),
    ).toEqual([
      'Ollama is app-managed but not running. Start it from Ollama.',
      'Camofox is app-managed but not running. Start it from Camofox.',
    ]);
    expect(proposalLines(dashboardFixture)).toContain(
      'proposal-1 | AAPL BUY | pending | $250.00 | confidence=0.82 | source=scanner',
    );
    expect(positionPlanCoverageLines(dashboardFixture)).toContain(
      'Missing Plans: MSFT',
    );
    expect(positionPlanCoverageLines({})).toEqual([
      'No position plan coverage snapshot is available yet.',
    ]);
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
    expect(renderActiveView('portfolio')).toContain('Exit Plan Coverage');
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

  it('shows accepted broker orders as refreshable proposal desk items', () => {
    const dashboardWithAcceptedOrder = {
      ...dashboardFixture,
      tradeProposals: {
        available: true,
        error: null,
        proposals: [
          {
            confidence: 0.77,
            execution_order_id: 'alpaca-paper-order-1',
            execution_outcome_status: 'accepted',
            notional: 500,
            proposal_id: 'proposal-refresh-1',
            reference_price: 250,
            side: 'buy',
            source: 'manual',
            status: 'approved',
            stop_loss: 240,
            symbol: 'NVDA',
            take_profit: 275,
            thesis: 'Accepted external paper order needs broker refresh.',
          },
        ],
      },
    };

    const markup = renderActiveView('proposals', dashboardWithAcceptedOrder);

    expect(markup).toContain('proposal-refresh-1');
    expect(markup).toContain('Refresh');
    expect(markup).toContain(
      'Refresh accepted broker order without resubmitting',
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

    render(withIntl(React.createElement(ControlRoom)));
    await screen.findByText('Agentic Trader Web GUI');

    fireEvent.click(screen.getByRole('button', { name: 'Refresh' }));
    await screen.findByText('Dashboard refreshed.');

    fireEvent.click(screen.getByRole('button', { name: 'One Shot' }));
    await screen.findByText('Strict one-shot cycle completed.');

    fireEvent.click(screen.getByRole('button', { name: 'Chat' }));
    await chooseSelectOption('Role', 'Risk Steward');
    fireEvent.change(
      screen.getByPlaceholderText('Ask for a review, status, or explanation.'),
      { target: { value: 'Explain current risk' } },
    );
    fireEvent.click(screen.getByRole('button', { name: 'Send' }));
    await screen.findByText('Operator reply received.');

    fireEvent.click(screen.getByRole('button', { name: 'Settings' }));
    await chooseSelectOption('Mode', 'apply');
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
      screen.getByPlaceholderText(
        'Review note required for approve, reject, reconcile, or refresh.',
      ),
      { target: { value: 'spread widened' } },
    );
    fireEvent.click(screen.getByRole('button', { name: 'Reject' }));
    await screen.findByText('AAPL proposal rejected.');

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(7));
    vi.unstubAllGlobals();
  });

  it('clears transient action messages when switching tabs', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(dashboardFixture))
      .mockResolvedValueOnce(
        jsonResponse(
          { error: 'RuntimeError: model failed to load' },
          { ok: false, status: 500 },
        ),
      );
    vi.stubGlobal('fetch', fetchMock);

    render(withIntl(React.createElement(ControlRoom)));
    await screen.findByText('Agentic Trader Web GUI');

    fireEvent.click(screen.getByRole('button', { name: 'Chat' }));
    fireEvent.change(
      screen.getByPlaceholderText('Ask for a review, status, or explanation.'),
      { target: { value: 'Explain current risk' } },
    );
    fireEvent.click(screen.getByRole('button', { name: 'Send' }));
    await screen.findByText('RuntimeError: model failed to load');

    fireEvent.click(screen.getByRole('button', { name: 'Proposals' }));
    await waitFor(() => {
      expect(
        screen.queryByText('RuntimeError: model failed to load'),
      ).toBeNull();
    });

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

    render(withIntl(React.createElement(ControlRoom)));
    const tokenInput = await screen.findByLabelText('Web GUI token');
    fireEvent.change(tokenInput, { target: { value: 'local-token' } });
    await act(async () => {
      fireEvent.submit(tokenInput.closest('form') as HTMLFormElement);
    });

    await screen.findByText('Agentic Trader Web GUI');
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
    vi.unstubAllGlobals();
  });

  it('does not abort a slow dashboard request on every polling tick', async () => {
    vi.useFakeTimers();
    const fetchMock = vi.fn(() => new Promise<Response>(() => {}));
    vi.stubGlobal('fetch', fetchMock);

    render(withIntl(React.createElement(ControlRoom)));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(7_500);
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('renders the initial control room shell while loading', () => {
    Object.defineProperty(globalThis, 'localStorage', {
      configurable: true,
      value: { getItem: () => 'tr', setItem: vi.fn(), clear: vi.fn() },
    });
    const html = renderToStaticMarkup(withIntl(React.createElement(ControlRoom)));
    expect(html).toContain('Agentic Trader');
    expect(html).toContain('Loading dashboard');
    expect(html).toContain('Local-first control room');
  });
});
