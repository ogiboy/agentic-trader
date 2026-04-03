import React, {useCallback, useEffect, useMemo, useState} from 'react';
import {Box, Text, useApp, useInput} from 'ink';
import {execFile} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {promisify} from 'node:util';

const execFileAsync = promisify(execFile);
const e = React.createElement;
const cliExecutable = process.env.AGENTIC_TRADER_CLI || 'agentic-trader';
const pythonExecutable = process.env.AGENTIC_TRADER_PYTHON;
const once = process.argv.includes('--once');
const projectRoot = fileURLToPath(new URL('..', import.meta.url));
const pages = ['overview', 'runtime', 'portfolio', 'review', 'chat'];
const personas = ['operator_liaison', 'regime_analyst', 'strategy_selector', 'risk_steward', 'portfolio_manager'];

async function execCli(args, {expectJson = false} = {}) {
  const attempts = [];
  if (cliExecutable) {
    attempts.push([cliExecutable, args]);
  }
  if (pythonExecutable) {
    attempts.push([pythonExecutable, ['-m', 'agentic_trader.cli', ...args]]);
  }

  let lastError;
  for (const [command, commandArgs] of attempts) {
    try {
      const {stdout, stderr} = await execFileAsync(command, commandArgs, {
        cwd: projectRoot,
        env: process.env,
        maxBuffer: 1024 * 1024 * 8,
      });
      return expectJson ? JSON.parse(stdout) : {stdout, stderr};
    } catch (error) {
      lastError = error;
      if (error && typeof error === 'object' && error.code !== 'ENOENT') {
        throw error;
      }
    }
  }

  throw lastError || new Error('No CLI command could be executed.');
}

async function runJsonCommand(args) {
  return execCli(args, {expectJson: true});
}

async function runTextCommand(args) {
  return execCli(args, {expectJson: false});
}

function defaultSymbolsFromPreferences(preferences) {
  const exchanges = preferences?.exchanges || [];
  const regions = preferences?.regions || [];
  if (exchanges.includes('BIST') || regions.includes('TR')) {
    return 'THYAO.IS,GARAN.IS';
  }
  if (exchanges.includes('NASDAQ') || exchanges.includes('NYSE') || regions.includes('US')) {
    return 'AAPL,MSFT';
  }
  return 'BTC-USD,ETH-USD';
}

async function loadDashboard() {
  const payload = await runJsonCommand(['dashboard-snapshot', '--log-limit', '14']);
  return {
    ...payload,
    loadedAt: new Date().toISOString(),
  };
}

function panel(title, lines, borderColor = 'cyan') {
  return e(
    Box,
    {
      flexDirection: 'column',
      borderStyle: 'round',
      borderColor,
      paddingX: 1,
      paddingY: 0,
      width: '100%',
    },
    e(Text, {color: borderColor, bold: true}, title),
    ...lines.map((line, index) =>
      e(Text, {key: `${title}-${index}`, wrap: 'truncate-end'}, String(line)),
    ),
  );
}

function renderLinesFallback(title, available, error, fallback) {
  if (available === false) {
    return [fallback, error || 'The runtime writer currently owns the database.'];
  }
  return null;
}

function OverviewPage({data}) {
  const doctor = data.doctor;
  const runtime = data.status;
  const preferences = data.preferences;
  const events = data.logs;
  const agentEvents = events.filter((event) => event.event_type.startsWith('agent_'));
  const latestAgentEvent = agentEvents[0];
  const latestOutcomeEvent = events.find((event) =>
    ['symbol_completed', 'position_closed', 'service_completed', 'service_failed'].includes(event.event_type),
  );

  return e(
    Box,
    {flexDirection: 'column', width: '100%'},
    e(
      Box,
      {width: '100%'},
      e(
        Box,
        {width: '50%', paddingRight: 1},
        panel(
          'CURRENT CYCLE',
          [
            `Runtime: ${runtime.runtime_state}`,
            `Live Process: ${runtime.live_process ? 'yes' : 'no'}`,
            `Current Symbol: ${runtime.state?.current_symbol ?? '-'}`,
            `Cycle Count: ${runtime.state?.cycle_count ?? '-'}`,
            `Status: ${runtime.status_message}`,
            `Current Note: ${runtime.state?.message ?? '-'}`,
            '',
            `Latest Agent Event: ${latestAgentEvent?.event_type ?? '-'}`,
            `Agent Message: ${latestAgentEvent?.message ?? 'No agent stage events yet.'}`,
            '',
            `Last Outcome: ${latestOutcomeEvent?.message ?? 'Waiting for a completed symbol or service result.'}`,
          ],
          runtime.runtime_state === 'active' ? 'green' : runtime.runtime_state === 'stale' ? 'yellow' : 'cyan',
        ),
      ),
      e(
        Box,
        {width: '50%', paddingLeft: 1},
        panel(
          'SYSTEM',
          [
            `Model: ${doctor.model}`,
            `Base URL: ${doctor.base_url}`,
            `Ollama Reachable: ${doctor.ollama_reachable ? 'yes' : 'no'}`,
            `Model Available: ${doctor.model_available ? 'yes' : 'no'}`,
            `Runtime Dir: ${doctor.runtime_dir}`,
            `Database: ${doctor.database}`,
            `Default Symbols: ${defaultSymbolsFromPreferences(preferences)}`,
          ],
          doctor.ollama_reachable && doctor.model_available ? 'green' : 'red',
        ),
      ),
    ),
    e(
      Box,
      {width: '100%', marginTop: 1},
      e(
        Box,
        {width: '100%'},
        panel(
          'AGENT ACTIVITY',
          agentEvents.length
            ? agentEvents.slice(0, 8).map((event) => `${event.created_at} | ${event.event_type} | ${event.message}`)
            : ['No live agent stage events yet.'],
          'magenta',
        ),
      ),
    ),
  );
}

function RuntimePage({data}) {
  const runtime = data.status;
  const events = data.logs;
  const reviewRecord = data.review.record;
  const recentSummary = reviewRecord?.artifacts?.review?.summary || 'No persisted review summary yet.';

  return e(
    Box,
    {flexDirection: 'column', width: '100%'},
    e(
      Box,
      {width: '100%'},
      e(
        Box,
        {width: '50%', paddingRight: 1},
        panel(
          'RUNTIME STATE',
          [
            `Runtime: ${runtime.runtime_state}`,
            `Live Process: ${runtime.live_process ? 'yes' : 'no'}`,
            `State: ${runtime.state?.state ?? '-'}`,
            `Current Symbol: ${runtime.state?.current_symbol ?? '-'}`,
            `Cycle Count: ${runtime.state?.cycle_count ?? '-'}`,
            `PID: ${runtime.state?.pid ?? '-'}`,
            `Updated: ${runtime.state?.updated_at ?? '-'}`,
            `Heartbeat Age: ${runtime.age_seconds ?? '-'}s`,
            `Stop Requested: ${runtime.state?.stop_requested ?? false}`,
            `Message: ${runtime.state?.message ?? '-'}`,
          ],
          'cyan',
        ),
      ),
      e(
        Box,
        {width: '50%', paddingLeft: 1},
        panel(
          'LAST REVIEW',
          [
            `Available: ${data.review.available !== false && reviewRecord ? 'yes' : 'no'}`,
            `Run ID: ${reviewRecord?.run_id ?? '-'}`,
            `Symbol: ${reviewRecord?.symbol ?? '-'}`,
            `Approved: ${reviewRecord?.approved ?? '-'}`,
            `Review Summary: ${recentSummary}`,
          ],
          'green',
        ),
      ),
    ),
    e(
      Box,
      {width: '100%', marginTop: 1},
      e(
        Box,
        {width: '100%'},
        panel(
          'RUNTIME EVENTS',
          events.length
            ? events.map((event) => `${event.created_at} | ${event.level} | ${event.event_type} | ${event.symbol ?? '-'} | ${event.message}`)
            : ['No runtime events recorded yet.'],
          'yellow',
        ),
      ),
    ),
  );
}

function PortfolioPage({data}) {
  const portfolio = data.portfolio;
  const riskReport = data.riskReport;
  const journal = data.journal;
  const preferences = data.preferences;
  const snapshot = portfolio.snapshot;
  const positions = portfolio.positions;

  const portfolioLines =
    renderLinesFallback('PORTFOLIO', portfolio.available, portfolio.error, 'Portfolio view is temporarily unavailable.') ||
    [
      `Cash: ${snapshot.cash.toFixed(2)}`,
      `Market Value: ${snapshot.market_value.toFixed(2)}`,
      `Equity: ${snapshot.equity.toFixed(2)}`,
      `Realized PnL: ${snapshot.realized_pnl.toFixed(2)}`,
      `Unrealized PnL: ${snapshot.unrealized_pnl.toFixed(2)}`,
      `Open Positions: ${positions.length}`,
    ];

  const riskLines =
    riskReport.available === false || !riskReport.report
      ? ['Risk report is temporarily unavailable.', riskReport.error || 'The runtime writer currently owns the database.']
      : [
          `Equity: ${riskReport.report.equity.toFixed(2)}`,
          `Gross Exposure: ${(riskReport.report.gross_exposure_pct * 100).toFixed(2)}%`,
          `Largest Position: ${(riskReport.report.largest_position_pct * 100).toFixed(2)}%`,
          `Drawdown: ${(riskReport.report.drawdown_from_peak_pct * 100).toFixed(2)}%`,
          `Warnings: ${riskReport.report.warnings.length}`,
        ];

  const journalLines =
    journal.available === false
      ? ['Trade journal is temporarily unavailable.', journal.error || 'The runtime writer currently owns the database.']
      : journal.entries.length
        ? journal.entries.map((entry) => `${entry.opened_at} | ${entry.symbol} | ${entry.journal_status} | ${entry.planned_side} | ${entry.realized_pnl ?? '-'}`)
        : ['No trade journal entries yet.'];

  const preferenceLines =
    renderLinesFallback('PREFERENCES', preferences.available, preferences.error, 'Preferences are temporarily unavailable.') ||
    [
      `Regions: ${(preferences.regions || []).join(', ') || '-'}`,
      `Exchanges: ${(preferences.exchanges || []).join(', ') || '-'}`,
      `Currencies: ${(preferences.currencies || []).join(', ') || '-'}`,
      `Risk: ${preferences.risk_profile}`,
      `Style: ${preferences.trade_style}`,
      `Behavior: ${preferences.behavior_preset}`,
      `Agent Profile: ${preferences.agent_profile}`,
    ];

  return e(
    Box,
    {flexDirection: 'column', width: '100%'},
    e(
      Box,
      {width: '100%'},
      e(Box, {width: '50%', paddingRight: 1}, panel('PORTFOLIO', portfolioLines, 'yellow')),
      e(Box, {width: '50%', paddingLeft: 1}, panel('RISK REPORT', riskLines, 'red')),
    ),
    e(
      Box,
      {width: '100%', marginTop: 1},
      e(Box, {width: '50%', paddingRight: 1}, panel('TRADE JOURNAL', journalLines.slice(0, 8), 'cyan')),
      e(Box, {width: '50%', paddingLeft: 1}, panel('PREFERENCES', preferenceLines, 'blue')),
    ),
  );
}

function ReviewPage({data}) {
  const review = data.review;
  const trace = data.trace;
  const reviewRecord = review.record;
  const traceRecord = trace.record;

  const reviewLines =
    review.available === false
      ? ['Run review is temporarily unavailable.', review.error || 'The runtime writer currently owns the database.']
      : reviewRecord
        ? [
            `Run ID: ${reviewRecord.run_id}`,
            `Created: ${reviewRecord.created_at}`,
            `Symbol: ${reviewRecord.symbol}`,
            `Approved: ${reviewRecord.approved}`,
            `Coordinator Focus: ${reviewRecord.artifacts.coordinator.market_focus}`,
            `Regime: ${reviewRecord.artifacts.regime.regime}`,
            `Strategy: ${reviewRecord.artifacts.strategy.strategy_family}`,
            `Manager Bias: ${reviewRecord.artifacts.manager.action_bias}`,
            `Review Summary: ${reviewRecord.artifacts.review.summary}`,
          ]
        : ['No persisted runs are available yet.'];

  const traceLines =
    trace.available === false
      ? ['Run trace is temporarily unavailable.', trace.error || 'The runtime writer currently owns the database.']
      : traceRecord?.artifacts?.agent_traces?.length
        ? traceRecord.artifacts.agent_traces.map(
            (stageTrace) =>
              `${stageTrace.role} | ${stageTrace.model_name} | fallback=${stageTrace.used_fallback} | ${stageTrace.output_json.replace(/\s+/g, ' ').slice(0, 72)}`,
          )
        : ['No persisted agent traces are available yet.'];

  return e(
    Box,
    {flexDirection: 'column', width: '100%'},
    e(
      Box,
      {width: '100%'},
      e(Box, {width: '50%', paddingRight: 1}, panel('LATEST RUN REVIEW', reviewLines, 'green')),
      e(Box, {width: '50%', paddingLeft: 1}, panel('AGENT TRACE', traceLines.slice(0, 8), 'magenta')),
    ),
  );
}

function ChatPage({persona, history, draft, chatBusy}) {
  return e(
    Box,
    {flexDirection: 'column', width: '100%'},
    e(
      Box,
      {width: '100%'},
      e(
        Box,
        {width: '100%'},
        panel(
          'OPERATOR CHAT',
          [
            `Persona: ${persona}`,
            'Type directly to write. Enter sends. Backspace deletes. [ and ] switch persona.',
            chatBusy ? 'Sending message to the operator surface...' : 'Ready.',
            '',
            ...(history.length
              ? history.slice(-8).flatMap((entry) => [`you: ${entry.user}`, `${entry.persona}: ${entry.response}`, ''])
              : ['No chat messages yet.']),
          ],
          'green',
        ),
      ),
    ),
    e(
      Box,
      {width: '100%', marginTop: 1},
      e(
        Box,
        {width: '100%'},
        panel('COMPOSER', [draft || ''], 'yellow'),
      ),
    ),
  );
}

function DashboardView({data, error, loadingText, page, actionMessage, busy, chatPersona, chatHistory, chatDraft, chatBusy}) {
  if (error) {
    return e(
      Box,
      {flexDirection: 'column'},
      e(Text, {color: 'red', bold: true}, 'AGENTIC TRADER // INK CONTROL ROOM'),
      e(Text, {color: 'red'}, `Error: ${error}`),
      e(Text, {color: 'gray'}, `CLI executable: ${cliExecutable}`),
    );
  }

  if (!data) {
    return e(
      Box,
      {flexDirection: 'column'},
      e(Text, {color: 'green', bold: true}, 'AGENTIC TRADER // INK CONTROL ROOM'),
      e(Text, {color: 'gray'}, loadingText),
    );
  }

  const pageIndex = pages.indexOf(page) + 1;
  const pageLabel =
    page === 'overview'
      ? 'Overview'
      : page === 'runtime'
        ? 'Runtime'
        : page === 'portfolio'
          ? 'Portfolio'
          : page === 'review'
            ? 'Review'
            : 'Chat';

  const view =
    page === 'overview'
      ? e(OverviewPage, {data})
      : page === 'runtime'
        ? e(RuntimePage, {data})
        : page === 'portfolio'
          ? e(PortfolioPage, {data})
          : page === 'review'
            ? e(ReviewPage, {data})
            : e(ChatPage, {persona: chatPersona, history: chatHistory, draft: chatDraft, chatBusy});

  return e(
    Box,
    {flexDirection: 'column', width: '100%'},
    e(Text, {color: 'green', bold: true}, 'AGENTIC TRADER // INK CONTROL ROOM'),
    e(
      Text,
      {color: 'gray'},
      `page ${pageIndex}/5: ${pageLabel}  |  1 overview  2 runtime  3 portfolio  4 review  5 chat  |  r refresh  s start  x stop  q quit${busy ? '  |  working...' : ''}`,
    ),
    actionMessage ? e(Text, {color: actionMessage.kind === 'error' ? 'red' : 'yellow'}, actionMessage.text) : null,
    view,
    e(Text, {color: 'gray'}, `Last refresh: ${data.loadedAt}`),
  );
}

function useDashboardState({interactive}) {
  const {exit} = useApp();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [refreshCount, setRefreshCount] = useState(0);
  const [page, setPage] = useState('overview');
  const [busy, setBusy] = useState(false);
  const [actionMessage, setActionMessage] = useState(null);
  const [chatPersona, setChatPersona] = useState('operator_liaison');
  const [chatHistory, setChatHistory] = useState([]);
  const [chatDraft, setChatDraft] = useState('');
  const [chatBusy, setChatBusy] = useState(false);
  const loadingText = useMemo(() => `Connecting to ${cliExecutable}...`, []);

  const refresh = useCallback(async () => {
    try {
      const next = await loadDashboard();
      setData(next);
      setError(null);
      if (once) {
        setTimeout(() => exit(), 50);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      if (once) {
        setTimeout(() => exit(), 50);
      }
    }
  }, [exit]);

  useEffect(() => {
    void refresh();
  }, [refresh, refreshCount]);

  useEffect(() => {
    if (!interactive) {
      return undefined;
    }
    const timer = setInterval(() => {
      setRefreshCount((current) => current + 1);
    }, 2000);
    return () => clearInterval(timer);
  }, [interactive]);

  const refreshNow = useCallback(() => {
    setRefreshCount((current) => current + 1);
  }, []);

  const runAction = useCallback(
    async (kind) => {
      if (!data || busy) {
        return;
      }
      setBusy(true);
      try {
        if (kind === 'start') {
          if (data.status.live_process) {
            setActionMessage({kind: 'info', text: `Runtime already active with PID ${data.status.state?.pid ?? '-'}.`});
          } else {
            const symbols = defaultSymbolsFromPreferences(data.preferences);
            await runTextCommand([
              'launch',
              '--symbols',
              symbols,
              '--interval',
              '1d',
              '--lookback',
              '180d',
              '--continuous',
              '--background',
              '--poll-seconds',
              '300',
            ]);
            setActionMessage({kind: 'info', text: `Background runtime launch requested for ${symbols}.`});
          }
        } else if (kind === 'stop') {
          if (!data.status.state?.pid) {
            setActionMessage({kind: 'info', text: 'No managed runtime is currently active.'});
          } else {
            await runTextCommand(['stop-service']);
            setActionMessage({kind: 'info', text: `Stop requested for PID ${data.status.state.pid}.`});
          }
        }
        const next = await loadDashboard();
        setData(next);
        setError(null);
      } catch (err) {
        setActionMessage({kind: 'error', text: err instanceof Error ? err.message : String(err)});
      } finally {
        setBusy(false);
      }
    },
    [busy, data],
  );

  const nextPage = useCallback(() => {
    setPage((current) => pages[(pages.indexOf(current) + 1) % pages.length]);
  }, []);

  const prevPage = useCallback(() => {
    setPage((current) => pages[(pages.indexOf(current) - 1 + pages.length) % pages.length]);
  }, []);

  return {
    data,
    error,
    loadingText,
    refreshNow,
    exit,
    page,
    setPage,
    nextPage,
    prevPage,
    runAction,
    busy,
    actionMessage,
    chatPersona,
    setChatPersona,
    chatHistory,
    setChatHistory,
    chatDraft,
    setChatDraft,
    chatBusy,
    setChatBusy,
  };
}

function InteractiveDashboardApp() {
  const {
    data,
    error,
    loadingText,
    refreshNow,
    exit,
    page,
    setPage,
    nextPage,
    prevPage,
    runAction,
    busy,
    actionMessage,
    chatPersona,
    setChatPersona,
    chatHistory,
    setChatHistory,
    chatDraft,
    setChatDraft,
    chatBusy,
    setChatBusy,
  } = useDashboardState({interactive: true});

  const sendChat = useCallback(async () => {
    const message = chatDraft.trim();
    if (!message || chatBusy) {
      return;
    }
    setChatBusy(true);
    try {
      const payload = await runJsonCommand(['chat', '--json', '--persona', chatPersona, '--message', message]);
      setChatHistory((current) => [...current, {user: payload.message, persona: payload.persona, response: payload.response}]);
      setChatDraft('');
    } catch (err) {
      setChatHistory((current) => [
        ...current,
        {
          user: message,
          persona: chatPersona,
          response: `Error: ${err instanceof Error ? err.message : String(err)}`,
        },
      ]);
      setChatDraft('');
    } finally {
      setChatBusy(false);
    }
  }, [chatBusy, chatDraft, chatPersona, setChatBusy, setChatDraft, setChatHistory]);

  useInput((input, key) => {
    if (key.rightArrow || input === '\t') {
      nextPage();
      return;
    }
    if (key.leftArrow) {
      prevPage();
      return;
    }
    if (['1', '2', '3', '4', '5'].includes(input) && page !== 'chat') {
      setPage(pages[Number(input) - 1]);
      return;
    }
    if (page === 'chat') {
      if (key.return) {
        void sendChat();
        return;
      }
      if (key.backspace || key.delete) {
        setChatDraft((current) => current.slice(0, -1));
        return;
      }
      if (input === '[') {
        setChatPersona((current) => personas[(personas.indexOf(current) - 1 + personas.length) % personas.length]);
        return;
      }
      if (input === ']') {
        setChatPersona((current) => personas[(personas.indexOf(current) + 1) % personas.length]);
        return;
      }
      if (!key.ctrl && !key.meta && input) {
        setChatDraft((current) => current + input);
        return;
      }
    }
    if (input.toLowerCase() === 'q') {
      exit();
      return;
    }
    if (input.toLowerCase() === 'r') {
      refreshNow();
      return;
    }
    if (input.toLowerCase() === 's') {
      void runAction('start');
      return;
    }
    if (input.toLowerCase() === 'x') {
      void runAction('stop');
      return;
    }
    if (['1', '2', '3', '4', '5'].includes(input)) {
      setPage(pages[Number(input) - 1]);
    }
  });

  return e(DashboardView, {
    data,
    error,
    loadingText,
    page,
    actionMessage,
    busy,
    chatPersona,
    chatHistory,
    chatDraft,
    chatBusy,
  });
}

function StaticDashboardApp() {
  const {data, error, loadingText, page, actionMessage, busy, chatPersona, chatHistory, chatDraft, chatBusy} = useDashboardState({interactive: false});
  return e(DashboardView, {data, error, loadingText, page, actionMessage, busy, chatPersona, chatHistory, chatDraft, chatBusy});
}

await import('ink').then(({render}) => {
  render(once ? e(StaticDashboardApp) : e(InteractiveDashboardApp));
});
