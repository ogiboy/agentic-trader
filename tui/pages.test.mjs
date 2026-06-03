import { describe, expect, it } from "vitest";

import { getPageView } from "./pages.mjs";
import { ChatPage } from "./pages/chat-page.mjs";
import { MemoryPage } from "./pages/memory-page.mjs";
import { OverviewPage } from "./pages/overview-page.mjs";
import { panel } from "./pages/panel.mjs";
import { PortfolioPage } from "./pages/portfolio-page.mjs";
import { ReviewPage } from "./pages/review-page.mjs";
import { RuntimePage } from "./pages/runtime-page.mjs";
import { SettingsPage } from "./pages/settings-page.mjs";

function textFrom(node) {
  if (node == null || typeof node === "boolean") {
    return [];
  }
  if (typeof node === "string" || typeof node === "number") {
    return [String(node)];
  }
  if (Array.isArray(node)) {
    return node.flatMap(textFrom);
  }
  return textFrom(node.props?.children);
}

function renderText(element) {
  return textFrom(element).join("\n");
}

function dashboardData() {
  return {
    agentActivity: {
      current_stage: "risk",
      current_stage_message: "checking guardrails",
      current_stage_status: "running",
      last_completed_message: "regime complete",
      last_completed_stage: "regime",
      last_outcome_message: "approved for paper review",
      last_outcome_type: "decision",
      recent_stage_events: [
        {
          created_at: "2026-06-01T13:00:00Z",
          event_type: "stage_started",
          level: "info",
          message: "risk started",
          symbol: "AAPL",
        },
      ],
      stage_statuses: [
        { message: "complete", stage: "regime", status: "done" },
        { message: "running", stage: "risk", status: "active" },
      ],
    },
    broker: {
      backend: "paper",
      external_paper: true,
      kill_switch_active: false,
      state: "ready",
    },
    calendar: {
      session: {
        is_tradable_now: true,
        state: "open",
        timezone: "America/New_York",
      },
    },
    canonicalAnalysis: {
      available: true,
      snapshot: {
        completeness_score: 0.98,
        disclosures: ["paper only"],
        fundamental: { attribution: { source_name: "filing" } },
        macro: { attribution: { source_name: "calendar" } },
        market: { attribution: { source_name: "alpaca" } },
        missing_sections: [],
        news_events: [{ title: "earnings" }],
        source_attributions: [
          {
            freshness: "fresh",
            provider_type: "market",
            source_name: "alpaca",
            source_role: "primary",
          },
        ],
        summary: "complete canonical analysis",
      },
    },
    doctor: {
      model_available: true,
      ollama_reachable: true,
      runtime_mode: "paper",
    },
    financeOps: {
      accounting: {
        cost_model: { fees: "paper", slippage_bps: 2 },
        mark_created_at: "2026-06-01T13:10:00Z",
        mark_source: "paper",
        rejection_evidence: "none",
      },
    },
    journal: {
      available: true,
      entries: [
        {
          journal_status: "open",
          opened_at: "2026-06-01T13:05:00Z",
          planned_side: "buy",
          realized_pnl: null,
          symbol: "AAPL",
        },
      ],
    },
    logs: [
      {
        created_at: "2026-06-01T13:06:00Z",
        event_type: "heartbeat",
        level: "info",
        message: "alive",
        symbol: "AAPL",
      },
    ],
    marketCache: { count: 2, mode: "warm" },
    marketContext: {
      available: true,
      contextPack: {
        anomaly_flags: ["none"],
        bars_analyzed: 30,
        bars_expected: 30,
        coverage_ratio: 1,
        data_quality_flags: [],
        higher_timeframe: "1wk",
        higher_timeframe_used: true,
        horizons: [{ horizon_bars: 5, return_pct: 1.2, trend_vote: "up" }],
        interval: "1d",
        lookback: "90d",
        summary: "constructive",
      },
    },
    memoryExplorer: {
      available: true,
      matches: [
        {
          created_at: "2026-05-31T13:00:00Z",
          score: 0.91,
          symbol: "AAPL",
        },
      ],
    },
    portfolio: {
      accounting: {},
      available: true,
      positions: [{ market_value: 1200, quantity: 4, symbol: "AAPL" }],
      snapshot: {
        cash: 10000,
        equity: 11200,
        market_value: 1200,
        realized_pnl: 120,
        unrealized_pnl: 80,
      },
    },
    preferences: {
      agent_profile: "balanced",
      agent_tone: "direct",
      available: true,
      behavior_preset: "paper",
      currencies: ["USD"],
      exchanges: ["NASDAQ"],
      intervention_style: "confirm",
      notes: "paper only",
      regions: ["US"],
      risk_profile: "moderate",
      sectors: ["Technology"],
      strictness_preset: "strict",
      trade_style: "swing",
    },
    recentRuns: {
      available: true,
      runs: [
        {
          approved: true,
          created_at: "2026-06-01T13:00:00Z",
          interval: "1d",
          run_id: "run-1",
          symbol: "AAPL",
        },
      ],
    },
    replay: {
      available: true,
      replay: {
        approved: true,
        consensus: { alignment_level: "strong" },
        final_rationale: "memory replay complete",
        final_side: "buy",
        manager_conflicts: [
          { conflict_type: "risk", severity: "low", summary: "size noted" },
        ],
        manager_override_notes: ["none"],
        snapshot: { higher_timeframe: "1wk", mtf_alignment: "aligned" },
        stages: [
          {
            retrieved_memories: ["prior"],
            role: "risk",
            shared_memory_bus: [],
            tool_outputs: [],
            used_fallback: false,
          },
        ],
      },
    },
    retrievalInspection: {
      available: true,
      stages: [
        {
          memory_notes: [],
          recent_runs: [],
          retrieval_explanations: [
            {
              explanation: {
                eligibility_reason: "same symbol",
                freshness: "recent",
                outcome_tag: "approved",
              },
            },
          ],
          retrieved_memories: ["prior risk memory"],
          role: "risk",
          shared_memory_bus: [],
        },
      ],
    },
    review: {
      available: true,
      record: {
        approved: true,
        artifacts: {
          consensus: { alignment_level: "strong" },
          coordinator: { market_focus: "AAPL 90d paper cycle" },
          fundamental: {
            evidence_vs_inference: {
              evidence: ["filing"],
              inference: ["quality"],
              uncertainty: ["macro"],
            },
            overall_bias: "constructive",
            red_flags: [],
          },
          manager: { action_bias: "buy" },
          regime: { regime: "risk-on" },
          review: {
            summary: "review complete",
            warnings: ["size small"],
          },
          snapshot: {
            higher_timeframe: "1wk",
            mtf_alignment: "aligned",
          },
          strategy: { strategy_family: "trend" },
        },
        created_at: "2026-06-01T13:00:00Z",
        run_id: "run-1",
        status: "complete",
        symbol: "AAPL",
      },
    },
    riskReport: {
      available: true,
      report: {
        drawdown_from_peak_pct: 0.01,
        equity: 11200,
        generated_at: "2026-06-01T13:10:00Z",
        gross_exposure_pct: 0.12,
        largest_position_pct: 0.1,
        warnings: ["within limits"],
      },
    },
    status: {
      age_seconds: 2,
      live_process: true,
      runtime_mode: "paper",
      runtime_state: "active",
      state: {
        background_mode: true,
        current_symbol: "AAPL",
        cycle_count: 3,
        interval: "1d",
        last_terminal_at: "2026-06-01T13:00:00Z",
        last_terminal_state: "complete",
        launch_count: 1,
        lookback: "90d",
        max_cycles: 5,
        message: "running",
        pid: 1234,
        restart_count: 0,
        runtime_mode: "paper",
        state: "running",
        stderr_log_path: "runtime/stderr.log",
        stdout_log_path: "runtime/stdout.log",
        stop_requested: false,
        symbols: ["AAPL", "MSFT"],
        updated_at: "2026-06-01T13:10:00Z",
      },
    },
    supervisor: {
      stderr_tail: [],
      stdout_tail: ["started"],
    },
    trace: {
      available: true,
      record: {
        artifacts: {
          agent_traces: [
            {
              model_name: "qwen3:8b",
              output_json: '{"status":"ok"}',
              role: "risk",
              used_fallback: false,
            },
          ],
        },
      },
    },
    tradeContext: {
      available: true,
      record: {
        consensus: { alignment_level: "strong" },
        execution_adapter: "paper",
        execution_backend: "paper",
        manager_rationale: "paper-approved",
        retrieved_memory_summary: { risk: ["prior"] },
        routed_models: { risk: "qwen3:8b" },
        tool_outputs: { broker: {} },
        trade_id: "trade-1",
      },
    },
    v1Readiness: {
      alpaca_paper: { ready: true },
      paper_operations: { allowed: true },
    },
  };
}

describe("Ink TUI pages", () => {
  it("routes dashboard page keys to page components", () => {
    const data = dashboardData();
    const chat = {
      busy: false,
      draft: "hello",
      history: [],
      persona: "operator_liaison",
    };
    const instruction = {
      busy: false,
      draft: "tighten risk",
      mode: "preview",
      result: null,
    };

    expect(
      getPageView({ page: "overview", data, chat, instruction }).type,
    ).toBe(OverviewPage);
    expect(getPageView({ page: "runtime", data, chat, instruction }).type).toBe(
      RuntimePage,
    );
    expect(
      getPageView({ page: "portfolio", data, chat, instruction }).type,
    ).toBe(PortfolioPage);
    expect(getPageView({ page: "review", data, chat, instruction }).type).toBe(
      ReviewPage,
    );
    expect(getPageView({ page: "memory", data, chat, instruction }).type).toBe(
      MemoryPage,
    );
    expect(
      getPageView({ page: "settings", data, chat, instruction }).type,
    ).toBe(SettingsPage);
    expect(getPageView({ page: "chat", data, chat, instruction }).type).toBe(
      ChatPage,
    );
  });

  it("renders primary page content from complete dashboard data", () => {
    const data = dashboardData();

    expect(renderText(OverviewPage({ data }))).toContain("CURRENT CYCLE");
    expect(renderText(RuntimePage({ data }))).toContain("RUNTIME EVENTS");
    expect(renderText(PortfolioPage({ data }))).toContain(
      "Cash (USD): 10000.00",
    );
    expect(renderText(ReviewPage({ data }))).toContain("CANONICAL ANALYSIS");
    expect(renderText(MemoryPage({ data }))).toContain("SIMILAR PAST RUNS");
    expect(
      renderText(
        SettingsPage({
          compact: true,
          data,
          draft: "tighten risk",
          instructionBusy: true,
          instructionMode: "apply",
          instructionResult: { should_update_preferences: true },
        }),
      ),
    ).toContain("Working...");
    expect(
      renderText(
        ChatPage({
          chatBusy: true,
          data,
          draft: "hello",
          history: [
            {
              persona: "operator_liaison",
              response: "ack",
              user: "status?",
            },
          ],
          persona: "operator_liaison",
        }),
      ),
    ).toContain("Sending message to the operator surface...");
    expect(renderText(panel("TEST", ["one"], "green"))).toContain("TEST");
  });

  it("renders fallback states for unavailable page data", () => {
    const data = dashboardData();
    const unavailable = {
      ...data,
      journal: { available: false, error: "journal locked" },
      memoryExplorer: { available: false, error: "memory locked" },
      portfolio: {
        ...data.portfolio,
        available: false,
        error: "portfolio locked",
      },
      preferences: {
        ...data.preferences,
        available: false,
        error: "prefs locked",
      },
      replay: { available: false, error: "replay locked" },
      retrievalInspection: { available: false, error: "inspection locked" },
      review: { available: false, error: "review locked" },
      riskReport: { available: false, error: "risk locked" },
      trace: { available: false, error: "trace locked" },
    };

    expect(renderText(PortfolioPage({ data: unavailable }))).toContain(
      "Portfolio view is temporarily unavailable.",
    );
    expect(renderText(ReviewPage({ data: unavailable }))).toContain(
      "review locked",
    );
    expect(renderText(MemoryPage({ data: unavailable }))).toContain(
      "memory locked",
    );
    expect(
      renderText(
        SettingsPage({
          compact: false,
          data: unavailable,
          draft: "",
          instructionBusy: false,
          instructionMode: "preview",
          instructionResult: null,
        }),
      ),
    ).toContain("Preferences are temporarily unavailable.");
    expect(
      renderText(
        ChatPage({
          chatBusy: false,
          data: {
            agentActivity: {},
            review: { available: false },
            tradeContext: { available: false },
          },
          draft: "",
          history: [],
          persona: "",
        }),
      ),
    ).toContain("No stage timeline recorded yet.");
  });
});
