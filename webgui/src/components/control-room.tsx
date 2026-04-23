"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type DashboardData = Record<string, any>;
type TabId = "overview" | "runtime" | "portfolio" | "review" | "memory" | "chat" | "settings";
type MessageTone = "neutral" | "good" | "warn" | "bad";

const tabs: Array<{ id: TabId; label: string }> = [
  { id: "overview", label: "Overview" },
  { id: "runtime", label: "Runtime" },
  { id: "portfolio", label: "Portfolio" },
  { id: "review", label: "Review" },
  { id: "memory", label: "Memory" },
  { id: "chat", label: "Chat" },
  { id: "settings", label: "Settings" },
];

const personas = [
  "operator_liaison",
  "regime_analyst",
  "strategy_selector",
  "risk_steward",
  "portfolio_manager",
];

const marketLensImage =
  "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1600&q=80";

function cx(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(" ");
}

function formatNumber(value: unknown, digits = 2): string {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "-";
  }
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  }).format(value);
}

function formatPercent(value: unknown, digits = 2): string {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "-";
  }
  return `${(value * 100).toFixed(digits)}%`;
}

function formatList(value: unknown): string {
  if (!Array.isArray(value) || value.length === 0) {
    return "-";
  }
  return value.join(", ");
}

function formatTimestamp(value: unknown): string {
  if (typeof value !== "string" || !value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

function tradeContextLines(record: Record<string, any> | null | undefined): string[] {
  if (!record) {
    return ["No persisted trade context is available yet."];
  }
  const routedModels = Object.entries(record.routed_models || {})
    .map(([role, model]) => `${role}:${model}`)
    .join(" | ");
  return [
    `Trade ID: ${record.trade_id ?? "-"}`,
    `Run ID: ${record.run_id ?? "-"}`,
    `Consensus: ${record.consensus?.alignment_level ?? "-"}`,
    `Manager Rationale: ${record.manager_rationale ?? "-"}`,
    `Execution Rationale: ${record.execution_rationale ?? "-"}`,
    `Execution Backend: ${record.execution_backend ?? "-"}`,
    `Execution Adapter: ${record.execution_adapter ?? "-"}`,
    `Execution Outcome: ${record.execution_outcome_status ?? "-"}`,
    `Rejection Reason: ${record.execution_rejection_reason ?? "-"}`,
    `Review Summary: ${record.review_summary ?? "-"}`,
    `Routed Models: ${routedModels || "-"}`,
  ];
}

function canonicalLines(snapshot: Record<string, any> | null | undefined): string[] {
  if (!snapshot) {
    return ["No canonical analysis snapshot is available yet."];
  }
  const sources = (snapshot.source_attributions || [])
    .slice(0, 6)
    .map(
      (source: Record<string, any>) =>
        `${source.provider_type}:${source.source_name} (${source.source_role}, ${source.freshness})`,
    );
  return [
    `Summary: ${snapshot.summary || "-"}`,
    `Completeness: ${snapshot.completeness_score ?? "-"}`,
    `Missing Sections: ${formatList(snapshot.missing_sections)}`,
    `Market Source: ${snapshot.market?.attribution?.source_name ?? "-"}`,
    `Fundamental Source: ${snapshot.fundamental?.attribution?.source_name ?? "-"}`,
    `Macro Source: ${snapshot.macro?.attribution?.source_name ?? "-"}`,
    `News Events: ${(snapshot.news_events || []).length}`,
    `Disclosures: ${(snapshot.disclosures || []).length}`,
    ...sources.map((source: string) => `Source: ${source}`),
  ];
}

function marketContextLines(pack: Record<string, any> | null | undefined): string[] {
  if (!pack) {
    return ["No persisted market context pack is available yet."];
  }
  const horizons = (pack.horizons || [])
    .slice(0, 4)
    .map(
      (item: Record<string, any>) =>
        `${item.horizon_bars} bars | ${item.trend_vote} | return=${item.return_pct ?? "-"} | drawdown=${item.max_drawdown_pct ?? "-"}`,
    );
  return [
    `Summary: ${pack.summary || "-"}`,
    `Lookback: ${pack.lookback ?? "-"} | Interval: ${pack.interval ?? "-"}`,
    `Window: ${pack.window_start ?? "-"} -> ${pack.window_end ?? "-"}`,
    `Coverage: ${pack.bars_analyzed ?? "-"} / ${pack.bars_expected ?? "-"} (${pack.coverage_ratio ?? "-"})`,
    `Quality: ${formatList(pack.data_quality_flags)}`,
    `Anomalies: ${formatList(pack.anomaly_flags)}`,
    ...horizons,
  ];
}

function normalizeChatHistory(data: DashboardData | null): Array<Record<string, string>> {
  const entries = data?.chatHistory?.entries || [];
  return [...entries].reverse().map((entry: Record<string, any>) => ({
    user: entry.user_message,
    persona: entry.persona,
    response: entry.response_text,
  }));
}

async function readJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "Request failed.");
  }
  return payload as T;
}

function Panel({
  title,
  accent,
  children,
}: {
  title: string;
  accent?: "lime" | "amber" | "cyan" | "rose";
  children: React.ReactNode;
}) {
  return (
    <section className={cx("panel", accent ? `panel--${accent}` : undefined)}>
      <div className="panel__title">{title}</div>
      <div className="panel__body">{children}</div>
    </section>
  );
}

function KeyValueList({ items }: { items: Array<[string, string]> }) {
  return (
    <dl className="kv-list">
      {items.map(([label, value]) => (
        <div className="kv-list__row" key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function TextList({ items }: { items: string[] }) {
  return (
    <ul className="text-list">
      {items.map((item, index) => (
        <li key={`${item}-${index}`}>{item}</li>
      ))}
    </ul>
  );
}

function JsonPreview({ value }: { value: unknown }) {
  return <pre className="json-preview">{JSON.stringify(value, null, 2)}</pre>;
}

export function ControlRoom() {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [tab, setTab] = useState<TabId>("overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<{ text: string; tone: MessageTone } | null>(
    null,
  );
  const [busy, setBusy] = useState<string | null>(null);
  const [chatDraft, setChatDraft] = useState("");
  const [chatPersona, setChatPersona] = useState("operator_liaison");
  const [chatHistory, setChatHistory] = useState<Array<Record<string, string>>>([]);
  const [instructionDraft, setInstructionDraft] = useState("");
  const [instructionMode, setInstructionMode] = useState<"preview" | "apply">("preview");
  const [instructionResult, setInstructionResult] = useState<Record<string, any> | null>(
    null,
  );
  const [lastLoadedAt, setLastLoadedAt] = useState<string>("-");

  const loadDashboard = useCallback(async () => {
    try {
      const payload = await readJson<DashboardData>("/api/dashboard");
      setDashboard(payload);
      setChatHistory(normalizeChatHistory(payload));
      setLastLoadedAt(new Date().toLocaleTimeString());
      setError(null);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : String(nextError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDashboard();
    const timer = setInterval(() => {
      void loadDashboard();
    }, 2500);
    return () => clearInterval(timer);
  }, [loadDashboard]);

  const runAction = useCallback(
    async (kind: "refresh" | "start" | "stop" | "restart" | "one-shot") => {
      if (kind === "refresh") {
        setBusy("refresh");
        await loadDashboard();
        setMessage({ text: "Dashboard refreshed.", tone: "neutral" });
        setBusy(null);
        return;
      }
      setBusy(kind);
      try {
        const result = await readJson<{ message: string; dashboard: DashboardData }>(
          "/api/runtime",
          {
            method: "POST",
            body: JSON.stringify({ kind }),
          },
        );
        setDashboard(result.dashboard);
        setChatHistory(normalizeChatHistory(result.dashboard));
        setMessage({ text: result.message, tone: "good" });
        setLastLoadedAt(new Date().toLocaleTimeString());
      } catch (nextError) {
        setMessage({
          text: nextError instanceof Error ? nextError.message : String(nextError),
          tone: "bad",
        });
      } finally {
        setBusy(null);
      }
    },
    [loadDashboard],
  );

  const sendChat = useCallback(async () => {
    const messageText = chatDraft.trim();
    if (!messageText) {
      return;
    }
    setBusy("chat");
    try {
      const result = await readJson<Record<string, string>>("/api/chat", {
        method: "POST",
        body: JSON.stringify({
          persona: chatPersona,
          message: messageText,
        }),
      });
      setChatHistory((current) => [
        ...current,
        {
          user: result.message,
          persona: result.persona,
          response: result.response,
        },
      ]);
      setChatDraft("");
      setMessage({ text: "Operator reply received.", tone: "good" });
      await loadDashboard();
    } catch (nextError) {
      setMessage({
        text: nextError instanceof Error ? nextError.message : String(nextError),
        tone: "bad",
      });
    } finally {
      setBusy(null);
    }
  }, [chatDraft, chatPersona, loadDashboard]);

  const sendInstruction = useCallback(async () => {
    const messageText = instructionDraft.trim();
    if (!messageText) {
      return;
    }
    setBusy("instruction");
    try {
      const result = await readJson<{ result: Record<string, any>; dashboard: DashboardData }>(
        "/api/instruct",
        {
          method: "POST",
          body: JSON.stringify({
            message: messageText,
            apply: instructionMode === "apply",
          }),
        },
      );
      setInstructionResult(result.result);
      setDashboard(result.dashboard);
      setChatHistory(normalizeChatHistory(result.dashboard));
      setInstructionDraft("");
      setMessage({
        text:
          instructionMode === "apply"
            ? "Preferences updated from operator instruction."
            : "Instruction preview ready.",
        tone: "good",
      });
      setLastLoadedAt(new Date().toLocaleTimeString());
    } catch (nextError) {
      setMessage({
        text: nextError instanceof Error ? nextError.message : String(nextError),
        tone: "bad",
      });
    } finally {
      setBusy(null);
    }
  }, [instructionDraft, instructionMode]);

  const currentCycle = useMemo<Array<[string, string]>>(
    () => [
      ["Runtime", dashboard?.status?.runtime_state ?? "-"],
      ["Mode", dashboard?.status?.runtime_mode ?? dashboard?.doctor?.runtime_mode ?? "-"],
      ["Current Symbol", dashboard?.status?.state?.current_symbol ?? "-"],
      ["Cycle Count", String(dashboard?.status?.state?.cycle_count ?? "-")],
      ["Status", dashboard?.status?.status_message ?? "-"],
      ["Current Stage", dashboard?.agentActivity?.current_stage ?? "-"],
      ["Stage Status", dashboard?.agentActivity?.current_stage_status ?? "-"],
      ["Last Outcome", dashboard?.agentActivity?.last_outcome_message ?? "Waiting for a completed symbol or service result."],
    ],
    [dashboard],
  );

  const system = useMemo<Array<[string, string]>>(
    () => [
      ["Model", dashboard?.doctor?.model ?? "-"],
      ["Base URL", dashboard?.doctor?.base_url ?? "-"],
      ["Ollama Reachable", dashboard?.doctor?.ollama_reachable ? "yes" : "no"],
      ["Model Available", dashboard?.doctor?.model_available ? "yes" : "no"],
      ["Broker Backend", dashboard?.broker?.backend ?? "-"],
      ["Broker State", dashboard?.broker?.state ?? "-"],
      ["Execution Mode", dashboard?.broker?.execution_mode ?? "-"],
      ["Market Session", dashboard?.calendar?.session?.session_state ?? "-"],
    ],
    [dashboard],
  );

  const activeView = useMemo(() => {
    if (!dashboard) {
      return null;
    }

    if (tab === "overview") {
      return (
        <div className="stack">
          <section className="market-ribbon">
            <img
              className="market-ribbon__image"
              src={marketLensImage}
              alt="Trading screens showing market data."
            />
            <div className="market-ribbon__overlay">
              <div>
                <p className="eyebrow">Operator Truth</p>
                <h1>Agentic Trader Web GUI</h1>
                <p className="market-ribbon__copy">
                  Local-first runtime, paper-first execution, and the same dashboard contract that powers CLI, Rich, and Ink.
                </p>
              </div>
              <div className="pill-row">
                <span className="pill">{dashboard.status?.runtime_mode ?? "-"}</span>
                <span className="pill">{dashboard.broker?.backend ?? "-"}</span>
                <span className="pill">{dashboard.calendar?.session?.venue ?? "session unknown"}</span>
                <span className="pill">{dashboard.doctor?.model ?? "-"}</span>
              </div>
            </div>
          </section>

          <div className="grid grid--2">
            <Panel title="Current Cycle" accent="lime">
              <KeyValueList items={currentCycle} />
            </Panel>
            <Panel title="System" accent="cyan">
              <KeyValueList items={system} />
            </Panel>
          </div>

          <Panel title="Agent Activity" accent="amber">
            <TextList
              items={
                dashboard.agentActivity?.recent_stage_events?.length
                  ? dashboard.agentActivity.recent_stage_events.map(
                      (event: Record<string, any>) =>
                        `${formatTimestamp(event.created_at)} | ${event.stage} | ${event.status} | ${event.message}`,
                    )
                  : ["No live agent stage events yet."]
              }
            />
          </Panel>
        </div>
      );
    }

    if (tab === "runtime") {
      return (
        <div className="grid grid--2">
          <Panel title="Runtime State" accent="lime">
            <KeyValueList
              items={[
                ["Runtime", dashboard.status?.runtime_state ?? "-"],
                ["Live Process", dashboard.status?.live_process ? "yes" : "no"],
                ["PID", String(dashboard.status?.state?.pid ?? "-")],
                ["Current Symbol", dashboard.status?.state?.current_symbol ?? "-"],
                ["Cycle Count", String(dashboard.status?.state?.cycle_count ?? "-")],
                ["Updated", formatTimestamp(dashboard.status?.state?.updated_at)],
                ["Stop Requested", String(dashboard.status?.state?.stop_requested ?? false)],
                ["Status", dashboard.status?.status_message ?? "-"],
              ]}
            />
          </Panel>
          <Panel title="Stage Flow" accent="cyan">
            <TextList
              items={(dashboard.agentActivity?.stage_statuses || []).map(
                (stage: Record<string, any>) =>
                  `${stage.stage} | ${stage.status} | ${stage.message}`,
              )}
            />
          </Panel>
          <Panel title="Runtime Events" accent="amber">
            <TextList
              items={
                dashboard.logs?.length
                  ? dashboard.logs.map(
                      (event: Record<string, any>) =>
                        `${formatTimestamp(event.created_at)} | ${event.level} | ${event.event_type} | ${event.symbol ?? "-"} | ${event.message}`,
                    )
                  : ["No runtime events recorded yet."]
              }
            />
          </Panel>
          <Panel title="Supervisor Tails" accent="rose">
            <TextList
              items={[
                ...(dashboard.supervisor?.stderr_tail?.length
                  ? dashboard.supervisor.stderr_tail
                  : ["No stderr tail."]),
                ...(dashboard.supervisor?.stdout_tail?.length
                  ? dashboard.supervisor.stdout_tail
                  : ["No stdout tail."]),
              ]}
            />
          </Panel>
        </div>
      );
    }

    if (tab === "portfolio") {
      return (
        <div className="grid grid--2">
          <Panel title="Portfolio" accent="lime">
            <KeyValueList
              items={[
                ["Cash", formatNumber(dashboard.portfolio?.snapshot?.cash)],
                ["Market Value", formatNumber(dashboard.portfolio?.snapshot?.market_value)],
                ["Equity", formatNumber(dashboard.portfolio?.snapshot?.equity)],
                ["Realized PnL", formatNumber(dashboard.portfolio?.snapshot?.realized_pnl)],
                ["Unrealized PnL", formatNumber(dashboard.portfolio?.snapshot?.unrealized_pnl)],
                ["Open Positions", String(dashboard.portfolio?.snapshot?.open_positions ?? "-")],
              ]}
            />
            <JsonPreview value={dashboard.portfolio?.positions || []} />
          </Panel>
          <Panel title="Risk Report" accent="rose">
            <KeyValueList
              items={[
                ["Equity", formatNumber(dashboard.riskReport?.report?.equity)],
                ["Gross Exposure", formatPercent(dashboard.riskReport?.report?.gross_exposure_pct)],
                ["Largest Position", formatPercent(dashboard.riskReport?.report?.largest_position_pct)],
                ["Drawdown", formatPercent(dashboard.riskReport?.report?.drawdown_from_peak_pct)],
                ["Warnings", String((dashboard.riskReport?.report?.warnings || []).length)],
              ]}
            />
            <TextList items={dashboard.riskReport?.report?.warnings || ["No warnings."]} />
          </Panel>
          <Panel title="Trade Journal" accent="amber">
            <TextList
              items={
                dashboard.journal?.entries?.length
                  ? dashboard.journal.entries.map(
                      (entry: Record<string, any>) =>
                        `${formatTimestamp(entry.opened_at)} | ${entry.symbol} | ${entry.journal_status} | ${entry.planned_side} | ${entry.realized_pnl ?? "-"}`,
                    )
                  : ["No trade journal entries yet."]
              }
            />
          </Panel>
          <Panel title="Preferences" accent="cyan">
            <KeyValueList
              items={[
                ["Regions", formatList(dashboard.preferences?.regions)],
                ["Exchanges", formatList(dashboard.preferences?.exchanges)],
                ["Currencies", formatList(dashboard.preferences?.currencies)],
                ["Risk", dashboard.preferences?.risk_profile ?? "-"],
                ["Style", dashboard.preferences?.trade_style ?? "-"],
                ["Behavior", dashboard.preferences?.behavior_preset ?? "-"],
                ["Tone", dashboard.preferences?.agent_tone ?? "-"],
                ["Strictness", dashboard.preferences?.strictness_preset ?? "-"],
              ]}
            />
          </Panel>
        </div>
      );
    }

    if (tab === "review") {
      return (
        <div className="grid grid--2">
          <Panel title="Latest Review" accent="lime">
            <TextList
              items={
                dashboard.review?.record
                  ? [
                      `Run ID: ${dashboard.review.record.run_id}`,
                      `Created: ${formatTimestamp(dashboard.review.record.created_at)}`,
                      `Symbol: ${dashboard.review.record.symbol}`,
                      `Approved: ${dashboard.review.record.approved}`,
                      `Coordinator Focus: ${dashboard.review.record.artifacts?.coordinator?.market_focus ?? "-"}`,
                      `Consensus: ${dashboard.review.record.artifacts?.consensus?.alignment_level ?? "-"}`,
                      `Review Summary: ${dashboard.review.record.artifacts?.review?.summary ?? "-"}`,
                    ]
                  : ["No persisted runs are available yet."]
              }
            />
          </Panel>
          <Panel title="Trade Context" accent="cyan">
            <TextList items={tradeContextLines(dashboard.tradeContext?.record)} />
          </Panel>
          <Panel title="Canonical Analysis" accent="amber">
            <TextList items={canonicalLines(dashboard.canonicalAnalysis?.snapshot)} />
          </Panel>
          <Panel title="Market Context Pack" accent="rose">
            <TextList items={marketContextLines(dashboard.marketContext?.contextPack)} />
          </Panel>
        </div>
      );
    }

    if (tab === "memory") {
      return (
        <div className="grid grid--2">
          <Panel title="Similar Memories" accent="lime">
            <TextList
              items={
                dashboard.memoryExplorer?.matches?.length
                  ? dashboard.memoryExplorer.matches.map(
                      (match: Record<string, any>) =>
                        `${formatTimestamp(match.created_at)} | ${match.symbol} | score=${match.similarity_score} | ${match.summary}`,
                    )
                  : ["No similar historical memories found yet."]
              }
            />
          </Panel>
          <Panel title="Retrieval Inspection" accent="cyan">
            <TextList
              items={
                dashboard.retrievalInspection?.stages?.length
                  ? dashboard.retrievalInspection.stages.flatMap((stage: Record<string, any>) => [
                      `${stage.role} | retrieved=${stage.retrieved_memories?.length ?? 0} | trade-memory=${stage.memory_notes?.length ?? 0} | shared-bus=${stage.shared_memory_bus?.length ?? 0} | recent-runs=${stage.recent_runs?.length ?? 0}`,
                      `Sample: ${
                        stage.retrieved_memories?.[0] ||
                        stage.memory_notes?.[0] ||
                        "No retrieval context attached."
                      }`,
                    ])
                  : ["No retrieval inspection data available yet."]
              }
            />
          </Panel>
        </div>
      );
    }

    if (tab === "chat") {
      return (
        <div className="grid grid--2">
          <Panel title="Operator Chat" accent="lime">
            <div className="form-row">
              <label className="field-label">
                Persona
                <select
                  value={chatPersona}
                  onChange={(event) => setChatPersona(event.target.value)}
                >
                  {personas.map((persona) => (
                    <option key={persona} value={persona}>
                      {persona}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div className="chat-log">
              {chatHistory.length ? (
                chatHistory.map((entry, index) => (
                  <article className="chat-bubble" key={`${entry.user}-${index}`}>
                    <div className="chat-bubble__meta">you</div>
                    <p>{entry.user}</p>
                    <div className="chat-bubble__meta">{entry.persona}</div>
                    <p>{entry.response}</p>
                  </article>
                ))
              ) : (
                <p className="empty-copy">No chat messages yet.</p>
              )}
            </div>
            <div className="composer">
              <textarea
                value={chatDraft}
                onChange={(event) => setChatDraft(event.target.value)}
                placeholder="Ask for a review, status, or explanation."
              />
              <button
                className="button button--solid"
                disabled={busy === "chat"}
                onClick={() => void sendChat()}
                type="button"
              >
                {busy === "chat" ? "Working..." : "Send"}
              </button>
            </div>
          </Panel>
          <Panel title="Live Agent Context" accent="cyan">
            <TextList
              items={[
                `Current Stage: ${dashboard.agentActivity?.current_stage ?? "-"}`,
                `Stage Status: ${dashboard.agentActivity?.current_stage_status ?? "-"}`,
                `Stage Detail: ${dashboard.agentActivity?.current_stage_message ?? "-"}`,
                `Last Completed: ${dashboard.agentActivity?.last_completed_stage ?? "-"}`,
                `Completed Detail: ${dashboard.agentActivity?.last_completed_message ?? "-"}`,
                `Tool Roles: ${Object.keys(dashboard.tradeContext?.record?.tool_outputs || {}).join(", ") || "-"}`,
                `Memory Roles: ${Object.keys(dashboard.tradeContext?.record?.retrieved_memory_summary || {}).join(", ") || "-"}`,
              ]}
            />
          </Panel>
        </div>
      );
    }

    return (
      <div className="grid grid--2">
        <Panel title="Preferences" accent="lime">
          <KeyValueList
            items={[
              ["Regions", formatList(dashboard.preferences?.regions)],
              ["Exchanges", formatList(dashboard.preferences?.exchanges)],
              ["Currencies", formatList(dashboard.preferences?.currencies)],
              ["Sectors", formatList(dashboard.preferences?.sectors)],
              ["Risk", dashboard.preferences?.risk_profile ?? "-"],
              ["Style", dashboard.preferences?.trade_style ?? "-"],
              ["Behavior", dashboard.preferences?.behavior_preset ?? "-"],
              ["Profile", dashboard.preferences?.agent_profile ?? "-"],
              ["Tone", dashboard.preferences?.agent_tone ?? "-"],
              ["Strictness", dashboard.preferences?.strictness_preset ?? "-"],
            ]}
          />
        </Panel>
        <Panel title="Recent Runs" accent="amber">
          <TextList
            items={
              dashboard.recentRuns?.runs?.length
                ? dashboard.recentRuns.runs.map(
                    (run: Record<string, any>) =>
                      `${formatTimestamp(run.created_at)} | ${run.symbol} | ${run.interval} | approved=${run.approved}`,
                  )
                : ["No recent runs recorded yet."]
            }
          />
        </Panel>
        <Panel title="Operator Instruction" accent="cyan">
          <TextList
            items={
              instructionResult
                ? [
                    `Summary: ${instructionResult.instruction?.summary ?? "-"}`,
                    `Update Preferences: ${instructionResult.instruction?.should_update_preferences ?? false}`,
                    `Requires Confirmation: ${instructionResult.instruction?.requires_confirmation ?? false}`,
                    `Applied: ${instructionResult.applied ? "yes" : "no"}`,
                    `Rationale: ${instructionResult.instruction?.rationale ?? "-"}`,
                  ]
                : [
                    "Type a safe operator instruction.",
                    "Examples:",
                    "make the system conservative",
                    "switch to capital preservation",
                  ]
            }
          />
        </Panel>
        <Panel title="Composer" accent="rose">
          <div className="form-row">
            <label className="field-label">
              Mode
              <select
                value={instructionMode}
                onChange={(event) =>
                  setInstructionMode(event.target.value as "preview" | "apply")
                }
              >
                <option value="preview">preview</option>
                <option value="apply">apply</option>
              </select>
            </label>
          </div>
          <div className="composer">
            <textarea
              value={instructionDraft}
              onChange={(event) => setInstructionDraft(event.target.value)}
              placeholder="Make the system more conservative and protective."
            />
            <button
              className="button button--solid"
              disabled={busy === "instruction"}
              onClick={() => void sendInstruction()}
              type="button"
            >
              {busy === "instruction" ? "Working..." : instructionMode === "apply" ? "Apply" : "Preview"}
            </button>
          </div>
        </Panel>
      </div>
    );
  }, [
    busy,
    chatDraft,
    chatHistory,
    chatPersona,
    currentCycle,
    dashboard,
    instructionDraft,
    instructionMode,
    instructionResult,
    sendChat,
    sendInstruction,
    system,
    tab,
  ]);

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="sidebar__brand">
          <div className="sidebar__eyebrow">Local-first control room</div>
          <div className="sidebar__title">Agentic Trader</div>
          <div className="sidebar__subtitle">Paper-first. Strict. Inspectable.</div>
        </div>

        <nav className="sidebar__nav" aria-label="Sections">
          {tabs.map((item) => (
            <button
              className={cx("nav-button", item.id === tab && "nav-button--active")}
              key={item.id}
              onClick={() => setTab(item.id)}
              type="button"
            >
              {item.label}
            </button>
          ))}
        </nav>

        <div className="sidebar__meta">
          <div>Runtime: {dashboard?.status?.runtime_state ?? "-"}</div>
          <div>Backend: {dashboard?.broker?.backend ?? "-"}</div>
          <div>Last refresh: {lastLoadedAt}</div>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div className="topbar__status">
            <span className="topbar__headline">{tabs.find((item) => item.id === tab)?.label}</span>
            <span className="chip">{dashboard?.status?.runtime_mode ?? dashboard?.doctor?.runtime_mode ?? "-"}</span>
            <span className="chip">{dashboard?.broker?.execution_mode ?? "-"}</span>
            <span className="chip">{dashboard?.broker?.message ?? "runtime unavailable"}</span>
          </div>
          <div className="topbar__actions">
            <button className="button" onClick={() => void runAction("refresh")} type="button">
              Refresh
            </button>
            <button className="button" disabled={busy !== null} onClick={() => void runAction("one-shot")} type="button">
              One Shot
            </button>
            <button className="button" disabled={busy !== null} onClick={() => void runAction("start")} type="button">
              Start
            </button>
            <button className="button" disabled={busy !== null} onClick={() => void runAction("stop")} type="button">
              Stop
            </button>
            <button className="button" disabled={busy !== null} onClick={() => void runAction("restart")} type="button">
              Restart
            </button>
          </div>
        </header>

        {message ? (
          <div className={cx("banner", `banner--${message.tone}`)}>{message.text}</div>
        ) : null}
        {error ? <div className="banner banner--bad">{error}</div> : null}

        {loading ? (
          <div className="loading">Loading dashboard...</div>
        ) : dashboard ? (
          activeView
        ) : (
          <div className="loading">Dashboard unavailable.</div>
        )}
      </main>
    </div>
  );
}
