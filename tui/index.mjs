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

async function runJsonCommand(args) {
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
      const {stdout} = await execFileAsync(command, commandArgs, {
        cwd: projectRoot,
        env: process.env,
        maxBuffer: 1024 * 1024 * 4,
      });
      return JSON.parse(stdout);
    } catch (error) {
      lastError = error;
      if (error && typeof error === 'object' && error.code !== 'ENOENT') {
        throw error;
      }
    }
  }

  throw lastError || new Error('No CLI command could be executed.');
}

async function loadDashboard() {
  const [doctor, status, logs, portfolio, preferences] = await Promise.all([
    runJsonCommand(['doctor', '--json']),
    runJsonCommand(['status', '--json']),
    runJsonCommand(['logs', '--json', '--limit', '8']),
    runJsonCommand(['portfolio', '--json']),
    runJsonCommand(['preferences', '--json']),
  ]);
  return {
    doctor,
    status,
    logs,
    portfolio,
    preferences,
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
    ...lines.map((line, index) => e(Text, {key: `${title}-${index}`}, line)),
  );
}

function StatusGrid({data}) {
  const doctor = data.doctor;
  const runtime = data.status;
  const snapshot = data.portfolio.snapshot;
  const positions = data.portfolio.positions;
  const preferences = data.preferences;
  const events = data.logs;

  return e(
    Box,
    {flexDirection: 'column', width: '100%'},
    e(
      Box,
      {marginBottom: 1, flexDirection: 'column'},
      e(Text, {color: 'green', bold: true}, 'AGENTIC TRADER // INK CONTROL ROOM'),
      e(Text, {color: 'gray'}, 'q quit  r refresh  auto-poll 2s'),
    ),
    e(
      Box,
      {width: '100%'},
      e(
        Box,
        {width: '50%', paddingRight: 1},
        panel(
          'SYSTEM',
          [
            `Model: ${doctor.model}`,
            `Base URL: ${doctor.base_url}`,
            `Ollama Reachable: ${doctor.ollama_reachable ? 'yes' : 'no'}`,
            `Model Available: ${doctor.model_available ? 'yes' : 'no'}`,
            `Runtime Dir: ${doctor.runtime_dir}`,
            `Database: ${doctor.database}`,
          ],
          doctor.ollama_reachable && doctor.model_available ? 'green' : 'red',
        ),
      ),
      e(
        Box,
        {width: '50%', paddingLeft: 1},
        panel(
          'RUNTIME',
          [
            `Runtime: ${runtime.runtime_state}`,
            `Live Process: ${runtime.live_process ? 'yes' : 'no'}`,
            `Last Recorded State: ${runtime.state?.state ?? '-'}`,
            `Current Symbol: ${runtime.state?.current_symbol ?? '-'}`,
            `Cycle Count: ${runtime.state?.cycle_count ?? '-'}`,
            `Status: ${runtime.status_message}`,
          ],
          runtime.runtime_state === 'active' ? 'green' : runtime.runtime_state === 'stale' ? 'yellow' : 'magenta',
        ),
      ),
    ),
    e(
      Box,
      {width: '100%', marginTop: 1},
      e(
        Box,
        {width: '50%', paddingRight: 1},
        panel(
          'PORTFOLIO',
          [
            `Cash: ${snapshot.cash.toFixed(2)}`,
            `Market Value: ${snapshot.market_value.toFixed(2)}`,
            `Equity: ${snapshot.equity.toFixed(2)}`,
            `Realized PnL: ${snapshot.realized_pnl.toFixed(2)}`,
            `Unrealized PnL: ${snapshot.unrealized_pnl.toFixed(2)}`,
            `Open Positions: ${positions.length}`,
          ],
          'yellow',
        ),
      ),
      e(
        Box,
        {width: '50%', paddingLeft: 1},
        panel(
          'PREFERENCES',
          [
            `Regions: ${(preferences.regions || []).join(', ') || '-'}`,
            `Exchanges: ${(preferences.exchanges || []).join(', ') || '-'}`,
            `Currencies: ${(preferences.currencies || []).join(', ') || '-'}`,
            `Risk: ${preferences.risk_profile}`,
            `Style: ${preferences.trade_style}`,
            `Behavior: ${preferences.behavior_preset}`,
            `Agent Profile: ${preferences.agent_profile}`,
          ],
          'blue',
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
          'cyan',
        ),
      ),
    ),
    e(Text, {color: 'gray'}, `Last refresh: ${data.loadedAt}`),
  );
}

function useDashboardState({interactive}) {
  const {exit} = useApp();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [refreshCount, setRefreshCount] = useState(0);
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
  }, []);

  return {
    data,
    error,
    loadingText,
    refreshNow: () => setRefreshCount((current) => current + 1),
    exit,
  };
}

function DashboardView({data, error, loadingText}) {
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

  return e(StatusGrid, {data});
}

function InteractiveDashboardApp() {
  const {data, error, loadingText, refreshNow, exit} = useDashboardState({interactive: true});
  useInput((input) => {
    if (input.toLowerCase() === 'q') {
      exit();
      return;
    }
    if (input.toLowerCase() === 'r') {
      refreshNow();
    }
  });
  return e(DashboardView, {data, error, loadingText});
}

function StaticDashboardApp() {
  const {data, error, loadingText} = useDashboardState({interactive: false});
  return e(DashboardView, {data, error, loadingText});
}

await import('ink').then(({render}) => {
  render(once ? e(StaticDashboardApp) : e(InteractiveDashboardApp));
});
