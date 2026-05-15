import { describe, expect, it } from 'vitest';

import {
  accountCurrency,
  defaultRuntimeInterval,
  defaultRuntimeLookback,
  defaultSingleSymbol,
  defaultSymbolsFromPreferences,
  failedCheckNames,
  formatMarketSession,
  formatMarketSessionWithTradable,
  formatMTFSnapshot,
  formatPersona,
  getAgentEventLines,
  getCurrentCycleLines,
  getExplorerLines,
  getInspectionLines,
  getInstructionResultLines,
  getJournalLines,
  getMarketContextLines,
  getPageLabel,
  getRecentRunsLines,
  getReplayLines,
  getReviewLines,
  getStatusBorderColor,
  getSystemLines,
  getSupervisorLogLines,
  getTraceLines,
  getTradeContextLines,
  handleChatInput,
  handleGlobalInput,
  handleSettingsInput,
  normalizeChatHistory,
  overviewRuntimeMode,
  providerLines,
  readinessLines,
  renderLinesFallback,
  renderUnavailableMessage,
  rotateInstructionMode,
  rotatePersona,
  sourceHealthSummaryLine,
} from './index.mjs';

describe('Ink TUI dashboard helpers', () => {
  it('derives defaults from operator preferences and dashboard state', () => {
    expect(formatPersona('operator_liaison')).toBe('Operator Assistant');
    expect(formatPersona('custom')).toBe('custom');
    expect(formatPersona('')).toBe('-');

    expect(defaultSymbolsFromPreferences({ exchanges: ['BIST'] })).toBe(
      'THYAO.IS,GARAN.IS',
    );
    expect(defaultSymbolsFromPreferences({ regions: ['US'] })).toBe('AAPL,MSFT');
    expect(defaultSymbolsFromPreferences({})).toBe('BTC-USD,ETH-USD');

    const dashboard = {
      marketContext: { contextPack: { interval: '1h', lookback: '90d' } },
      preferences: { currencies: ['EUR'], regions: ['US'] },
      review: { record: { symbol: 'MSFT' } },
      status: { state: { current_symbol: 'AAPL' } },
    };
    expect(accountCurrency(dashboard)).toBe('EUR');
    expect(defaultSingleSymbol(dashboard)).toBe('AAPL');
    expect(defaultRuntimeInterval(dashboard)).toBe('1h');
    expect(defaultRuntimeLookback(dashboard)).toBe('90d');
  });

  it('formats supervisor, trade-context, and market-context evidence lines', () => {
    expect(getSupervisorLogLines({ stderr_tail: ['one', 'two', 'three', 'four'] })).toEqual([
      'stderr:',
      'two',
      'three',
      'four',
    ]);
    expect(getSupervisorLogLines({ stdout_tail: ['started'] })).toEqual([
      'stdout:',
      'started',
    ]);
    expect(getSupervisorLogLines({})).toEqual(['No daemon log tail yet.']);

    expect(getTradeContextLines({ available: false, error: 'database offline' })).toEqual([
      'unavailable',
      'database offline',
    ]);
    expect(getTradeContextLines({})).toEqual([
      'No persisted trade context is available yet.',
    ]);
    expect(
      getTradeContextLines({
        record: {
          consensus: { alignment_level: 'strong' },
          execution_adapter: 'paper',
          execution_backend: 'paper',
          execution_outcome_status: 'blocked',
          execution_rationale: 'risk guard',
          manager_rationale: 'hold',
          retrieved_memory_summary: { risk: [] },
          review_summary: 'reviewed',
          routed_models: { manager: 'qwen3:8b' },
          run_id: 'run-1',
          tool_outputs: { broker: {} },
          trade_id: 'trade-1',
        },
      }),
    ).toContain('Routed Models: manager:qwen3:8b');

    expect(getMarketContextLines({ available: false, error: 'no source' })).toEqual([
      'unavailable',
      'no source',
    ]);
    expect(getMarketContextLines({})).toEqual([
      'No persisted Market Context Pack is available yet.',
    ]);
    expect(
      getMarketContextLines({
        contextPack: {
          anomaly_flags: ['gap'],
          bars_analyzed: 28,
          bars_expected: 30,
          coverage_ratio: 0.93,
          data_quality_flags: ['short_window'],
          higher_timeframe: '1wk',
          higher_timeframe_used: true,
          horizons: [{ horizon_bars: 5, max_drawdown_pct: -2, return_pct: 1, trend_vote: 'up' }],
          interval: '1d',
          interval_semantics: 'cash',
          lookback: '30d',
          summary: 'constructive',
          window_end: '2026-05-15',
          window_start: '2026-04-15',
        },
      }),
    ).toContain('5b up return=1 drawdown=-2');
  });

  it('handles keyboard input helpers and page/status formatting', () => {
    expect(rotatePersona('operator_liaison', 1)).toBe('regime_analyst');
    expect(rotatePersona('operator_liaison', -1)).toBe('portfolio_manager');
    expect(rotateInstructionMode('preview', 1)).toBe('apply');
    expect(rotateInstructionMode('preview', -1)).toBe('apply');
    expect(getPageLabel('review')).toBe('Review');
    expect(getPageLabel('missing')).toBe('Unknown');
    expect(getStatusBorderColor('active')).toBe('green');
    expect(getStatusBorderColor('stale')).toBe('yellow');
    expect(getStatusBorderColor('inactive')).toBe('cyan');

    let chatDraft = 'ab';
    let chatPersona = 'operator_liaison';
    let chatSent = 0;
    const chatHandlers = {
      sendChat: () => {
        chatSent += 1;
      },
      setChatDraft: (updater) => {
        chatDraft = updater(chatDraft);
      },
      setChatPersona: (updater) => {
        chatPersona = updater(chatPersona);
      },
    };
    expect(handleChatInput('', { return: true }, chatHandlers)).toBe(true);
    expect(chatSent).toBe(1);
    expect(handleChatInput('', { backspace: true }, chatHandlers)).toBe(true);
    expect(chatDraft).toBe('a');
    expect(handleChatInput(']', {}, chatHandlers)).toBe(true);
    expect(chatPersona).toBe('regime_analyst');
    expect(handleChatInput('[', {}, chatHandlers)).toBe(true);
    expect(chatPersona).toBe('operator_liaison');
    expect(handleChatInput('x', {}, chatHandlers)).toBe(true);
    expect(chatDraft).toBe('ax');
    expect(handleChatInput('x', { ctrl: true }, chatHandlers)).toBe(false);

    let instructionDraft = 'risk';
    let instructionMode = 'preview';
    let instructionSent = 0;
    const settingsHandlers = {
      sendInstruction: () => {
        instructionSent += 1;
      },
      setInstructionDraft: (updater) => {
        instructionDraft = updater(instructionDraft);
      },
      setInstructionMode: (updater) => {
        instructionMode = updater(instructionMode);
      },
    };
    expect(
      handleSettingsInput('', { return: true }, settingsHandlers),
    ).toBe(true);
    expect(instructionSent).toBe(1);
    expect(
      handleSettingsInput('', { delete: true }, settingsHandlers),
    ).toBe(true);
    expect(instructionDraft).toBe('ris');
    expect(handleSettingsInput(']', {}, settingsHandlers)).toBe(true);
    expect(instructionMode).toBe('apply');
    expect(handleSettingsInput('!', {}, settingsHandlers)).toBe(true);
    expect(instructionDraft).toBe('ris!');
    expect(handleSettingsInput('x', { meta: true }, settingsHandlers)).toBe(
      false,
    );

    const actions = [];
    const globalHandlers = {
      exit: () => actions.push('exit'),
      refreshNow: () => actions.push('refresh'),
      runAction: (kind) => actions.push(kind),
      setPage: (page) => actions.push(page),
    };
    for (const input of ['q', 'r', 'o', 's', 'x', 'R', '5']) {
      expect(handleGlobalInput(input, globalHandlers)).toBe(true);
    }
    expect(handleGlobalInput('?', globalHandlers)).toBe(false);
    expect(actions).toEqual([
      'exit',
      'refresh',
      'one-shot',
      'start',
      'stop',
      'restart',
      'memory',
    ]);
  });

  it('formats review, replay, memory, journal, and instruction panels', () => {
    const reviewRecord = {
      approved: true,
      artifacts: {
        consensus: { alignment_level: 'aligned' },
        coordinator: { market_focus: 'trend' },
        fundamental: {
          evidence_vs_inference: { evidence: ['filing'], inference: ['margin'] },
          overall_bias: 'constructive',
          red_flags: [],
        },
        manager: { action_bias: 'buy' },
        regime: { regime: 'trend_up' },
        review: { summary: 'reviewed' },
        strategy: { strategy_family: 'trend_following' },
      },
      created_at: '2026-05-15T00:00:00Z',
      run_id: 'run-1',
      symbol: 'AAPL',
    };
    expect(getReviewLines()).toEqual(['No persisted runs are available yet.']);
    expect(getReviewLines(reviewRecord)).toContain('Consensus: aligned');

    const traceRecord = {
      artifacts: {
        agent_traces: [
          {
            model_name: 'qwen3:8b',
            output_json: '{ "summary": "test output" }',
            role: 'manager',
            used_fallback: false,
          },
        ],
      },
    };
    expect(getTraceLines({})).toEqual([
      'No persisted agent traces are available yet.',
    ]);
    expect(getTraceLines(traceRecord)[0]).toContain('manager | qwen3:8b');

    const replayState = {
      approved: false,
      consensus: { alignment_level: 'mixed' },
      final_rationale: 'wait',
      final_side: 'hold',
      manager_conflicts: [
        { conflict_type: 'risk', severity: 'high', summary: 'too large' },
      ],
      manager_override_notes: ['trim size'],
      snapshot: { higher_timeframe: '1wk', mtf_alignment: 'neutral' },
      stages: [
        {
          retrieved_memories: ['m1'],
          role: 'risk',
          shared_memory_bus: [],
          tool_outputs: ['tool'],
          used_fallback: false,
        },
      ],
    };
    expect(getReplayLines()).toEqual(['No replayable run is available yet.']);
    expect(getReplayLines(replayState)).toContain('Conflict Count: 1');

    expect(getExplorerLines({ matches: [] })).toEqual([
      'No similar historical memories found yet.',
    ]);
    expect(
      getExplorerLines({
        matches: [
          {
            created_at: 'now',
            explanation: { eligibility_reason: 'same regime' },
            regime: 'trend',
            similarity_score: 0.9,
            strategy_family: 'momentum',
            summary: 'prior setup',
            symbol: 'AAPL',
          },
        ],
      })[0],
    ).toContain('same regime');

    expect(getInspectionLines({ stages: [] })).toEqual([
      'No retrieval inspection data available yet.',
    ]);
    expect(
      getInspectionLines({
        stages: [
          {
            memory_notes: [],
            recent_runs: ['run-1'],
            retrieved_memories: ['memory sample'],
            retrieval_explanations: [
              {
                explanation: {
                  eligibility_reason: 'fresh',
                  freshness: 'fresh',
                  outcome_tag: 'winner',
                },
              },
            ],
            role: 'manager',
            shared_memory_bus: ['bus'],
          },
        ],
      }),
    ).toContain('  Why: fresh | freshness=fresh | outcome=winner');

    expect(getJournalLines({ entries: [] })).toEqual([
      'No trade journal entries yet.',
    ]);
    expect(
      getJournalLines({
        entries: [
          {
            journal_status: 'open',
            opened_at: 'today',
            planned_side: 'buy',
            realized_pnl: null,
            symbol: 'AAPL',
          },
        ],
      }),
    ).toEqual(['today | AAPL | open | buy | -']);

    expect(getRecentRunsLines({ available: false, error: 'locked' })).toEqual([
      'unavailable',
      'locked',
    ]);
    expect(getRecentRunsLines({ runs: [] })).toEqual([
      'No recent runs recorded yet.',
    ]);
    expect(
      getRecentRunsLines({
        runs: [
          {
            approved: true,
            created_at: 'today',
            interval: '1d',
            run_id: 'run-1',
            symbol: 'AAPL',
          },
        ],
      }),
    ).toEqual(['today | AAPL | 1d | approved=true | run-1']);

    expect(getInstructionResultLines()).toContain(
      'Type a safe operator instruction.',
    );
    expect(
      getInstructionResultLines({
        applied: true,
        instruction: {
          preference_update: { risk_profile: 'conservative', sectors: ['tech'] },
          rationale: 'safer',
          requires_confirmation: false,
          should_update_preferences: true,
          summary: 'reduce risk',
        },
      }),
    ).toContain('Preference Update: risk_profile=conservative | sectors=tech');
  });

  it('summarizes readiness, provider, runtime, system, and history data', () => {
    expect(renderUnavailableMessage()).toEqual([
      'unavailable',
      'The runtime writer currently owns the database.',
    ]);
    expect(renderLinesFallback('X', false, '', 'fallback')).toEqual([
      'fallback',
      'The runtime writer currently owns the database.',
    ]);
    expect(renderLinesFallback('X', true, '', 'fallback')).toBeNull();
    expect(failedCheckNames({ checks: [] })).toBe('-');
    expect(
      failedCheckNames({
        checks: [
          { blocking: true, name: 'strict_llm', passed: false },
          { blocking: false, name: 'optional', passed: false },
          { name: 'provider', passed: false },
        ],
      }),
    ).toBe('strict_llm, provider');
    expect(sourceHealthSummaryLine({ fresh: 2, missing: 1, unknown: 3 })).toBe(
      'fresh 2 / missing 1 / unknown 3',
    );
    expect(sourceHealthSummaryLine()).toBe('-');
    expect(formatMarketSession()).toBe('unavailable');
    expect(
      formatMarketSession({ session_state: 'open', venue: 'NYSE' }),
    ).toBe('NYSE open');
    expect(
      formatMarketSessionWithTradable({
        session_state: 'closed',
        tradable_now: false,
        venue: 'BIST',
      }),
    ).toBe('BIST closed tradable=false');
    expect(formatMTFSnapshot()).toBe('-');
    expect(
      formatMTFSnapshot({ higher_timeframe: '1wk', mtf_alignment: 'bullish' }),
    ).toBe('bullish @ 1wk');

    const data = {
      agentActivity: {
        current_stage: 'manager',
        current_stage_message: 'sizing',
        current_stage_status: 'running',
        last_completed_message: 'risk ok',
        last_completed_stage: 'risk',
        last_outcome_message: 'completed',
        last_outcome_type: 'symbol_completed',
      },
      broker: {
        backend: 'paper',
        external_paper: true,
        healthcheck: { message: 'healthy' },
        kill_switch_active: false,
        state: 'ready',
      },
      calendar: {
        session: { session_state: 'open', tradable_now: true, venue: 'NYSE' },
      },
      camofoxService: {
        app_owned: true,
        base_url: 'http://127.0.0.1:9377',
        message: 'ready',
      },
      doctor: {
        base_url: 'http://127.0.0.1:11434/v1',
        database: '/tmp/db',
        model: 'qwen3:8b',
        model_available: true,
        ollama_reachable: true,
        runtime_dir: '/tmp/runtime',
        runtime_mode: 'operation',
      },
      marketCache: { count: 4 },
      marketContext: {
        contextPack: {
          data_quality_flags: ['fresh'],
          summary: 'trend intact',
        },
      },
      news: { mode: 'off' },
      preferences: {
        exchanges: ['NASDAQ'],
        regions: ['US'],
      },
      providerDiagnostics: {
        configured_keys: { alpaca: true, finnhub: false, fmp: true },
        market_data: { selected_provider: 'alpaca', selected_role: 'primary' },
        news: { mode: 'firecrawl' },
        warnings: ['fallback source'],
      },
      research: {
        backend: 'noop',
        source_health_summary: { fresh: 1, missing: 0, unknown: 0 },
        status: 'disabled',
      },
      review: {
        record: {
          artifacts: {
            consensus: { alignment_level: 'strong' },
            snapshot: { higher_timeframe: '1wk', mtf_alignment: 'bullish' },
          },
        },
      },
      status: {
        live_process: true,
        runtime_state: 'active',
        state: {
          current_symbol: 'AAPL',
          cycle_count: 7,
          interval: '1d',
          lookback: '90d',
          message: 'working',
          runtime_mode: 'operation',
        },
        status_message: 'running',
      },
      v1Readiness: {
        alpaca_paper: {
          checks: [{ name: 'alpaca_key', passed: false }],
          ready: false,
        },
        paper_operations: { allowed: true, checks: [] },
      },
    };

    expect(readinessLines(data)).toContain('Can run local paper cycle: yes');
    expect(providerLines(data)).toContain('fallback source');
    expect(overviewRuntimeMode(data.status, data)).toBe('operation');
    expect(getCurrentCycleLines(data, true)).toContain('Runtime: active');
    expect(getCurrentCycleLines(data, false)).toContain(
      'Context Pack: trend intact',
    );
    expect(getSystemLines(data, true)).toContain('Ollama Reachable: yes');
    expect(getSystemLines(data, false)).toContain('Cached Snapshots: 4');
    expect(getAgentEventLines([])).toEqual([
      'No live agent stage events yet.',
    ]);
    expect(
      getAgentEventLines([
        {
          created_at: 'now',
          message: 'done',
          stage: 'review',
          status: 'completed',
        },
      ]),
    ).toEqual(['now | review | completed | done']);
    expect(
      normalizeChatHistory({
        chatHistory: {
          entries: [
            {
              persona: 'operator_liaison',
              response_text: 'two',
              user_message: 'second',
            },
            {
              persona: 'risk_steward',
              response_text: 'one',
              user_message: 'first',
            },
          ],
        },
      }),
    ).toEqual([
      { persona: 'risk_steward', response: 'one', user: 'first' },
      { persona: 'operator_liaison', response: 'two', user: 'second' },
    ]);
  });
});
