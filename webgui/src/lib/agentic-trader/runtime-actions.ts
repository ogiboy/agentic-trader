import { asRecord, asString, asStringArray, type JsonRecord } from '../json-record';
import { execTraderWithDbLockRetry } from './cli-exec';
import { getDashboardSnapshot } from './dashboard';

function defaultSymbolsFromPreferences(preferences: {
  exchanges?: unknown;
  regions?: unknown;
}): string {
  const v1DefaultSymbols = 'AAPL,MSFT';
  if (process.env.AGENTIC_TRADER_WEBGUI_GLOBAL_SYMBOL_DEFAULTS !== '1') {
    return v1DefaultSymbols;
  }
  const exchanges = asStringArray(preferences.exchanges);
  const regions = asStringArray(preferences.regions);
  if (exchanges.includes('BIST') || regions.includes('TR')) {
    return 'THYAO.IS,GARAN.IS';
  }
  if (
    exchanges.includes('NASDAQ') ||
    exchanges.includes('NYSE') ||
    regions.includes('US')
  ) {
    return 'AAPL,MSFT';
  }
  return v1DefaultSymbols;
}

function defaultSingleSymbol(data: JsonRecord): string {
  const status = asRecord(data.status);
  const state = asRecord(status.state);
  const tradeContext = asRecord(data.tradeContext);
  const tradeRecord = asRecord(tradeContext.record);
  const review = asRecord(data.review);
  const reviewRecord = asRecord(review.record);
  return (
    asString(state.current_symbol, '') ||
    asString(tradeRecord.symbol, '') ||
    asString(reviewRecord.symbol, '') ||
    defaultSymbolsFromPreferences(asRecord(data.preferences)).split(',')[0]
  );
}

function defaultRuntimeInterval(data: JsonRecord): string {
  const status = asRecord(data.status);
  const state = asRecord(status.state);
  const marketContext = asRecord(data.marketContext);
  const contextPack = asRecord(marketContext.contextPack);
  return (
    asString(state.interval, '') ||
    asString(contextPack.interval, '') ||
    '1d'
  );
}

function defaultRuntimeLookback(data: JsonRecord): string {
  const status = asRecord(data.status);
  const state = asRecord(status.state);
  const marketContext = asRecord(data.marketContext);
  const contextPack = asRecord(marketContext.contextPack);
  return (
    asString(state.lookback, '') ||
    asString(contextPack.lookback, '') ||
    '180d'
  );
}

function isTraderRunning(data: JsonRecord): boolean {
  const status = asRecord(data.status);
  return (
    status.live_process === true && status.runtime_state === 'active'
  );
}

export async function runRuntimeAction(kind: string): Promise<{
  message: string;
  dashboard: JsonRecord;
}> {
  const data = await getDashboardSnapshot();
  const status = asRecord(data.status);
  const state = asRecord(status.state);

  if (kind === 'start') {
    if (isTraderRunning(data)) {
      return {
        message: `Runtime already active with PID ${asString(state.pid)}.`,
        dashboard: data,
      };
    }
    const symbols = defaultSymbolsFromPreferences(asRecord(data.preferences));
    const interval = defaultRuntimeInterval(data);
    const lookback = defaultRuntimeLookback(data);
    await execTraderWithDbLockRetry(
      [
        'launch',
        '--symbols',
        symbols,
        '--interval',
        interval,
        '--lookback',
        lookback,
        '--continuous',
        '--background',
        '--poll-seconds',
        '300',
      ],
      { timeoutMs: 60_000 },
    );
    return {
      message: `Background runtime launch requested for ${symbols} (${interval}, ${lookback}).`,
      dashboard: await getDashboardSnapshot(),
    };
  }

  if (kind === 'stop') {
    if (!isTraderRunning(data)) {
      return {
        message: 'No managed runtime is currently active.',
        dashboard: data,
      };
    }
    await execTraderWithDbLockRetry(['stop-service'], { timeoutMs: 30_000 });
    return {
      message: `Stop requested for PID ${asString(state.pid)}.`,
      dashboard: await getDashboardSnapshot(),
    };
  }

  if (kind === 'restart') {
    if (Array.isArray(state.symbols) && state.symbols.length) {
      await execTraderWithDbLockRetry(['restart-service'], {
        timeoutMs: 30_000,
      });
      return {
        message: 'Background runtime restart requested.',
        dashboard: await getDashboardSnapshot(),
      };
    }
    return {
      message: 'No saved runtime launch config is available yet.',
      dashboard: data,
    };
  }

  if (kind === 'one-shot') {
    if (isTraderRunning(data)) {
      return {
        message: `Runtime already active with PID ${asString(state.pid)}. Stop it before running a one-shot cycle.`,
        dashboard: data,
      };
    }
    const symbol = defaultSingleSymbol(data);
    const interval = defaultRuntimeInterval(data);
    const lookback = defaultRuntimeLookback(data);
    await execTraderWithDbLockRetry(
      [
        'run',
        '--symbol',
        symbol,
        '--interval',
        interval,
        '--lookback',
        lookback,
      ],
      { timeoutMs: 240_000 },
    );
    return {
      message: `Strict one-shot cycle completed for ${symbol} (${interval}, ${lookback}).`,
      dashboard: await getDashboardSnapshot(),
    };
  }

  throw new Error(`Unsupported runtime action: ${kind}`);
}
