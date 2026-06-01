/* eslint-disable @typescript-eslint/no-explicit-any -- Dashboard payloads are schema-loose JSON today */
import { execTraderWithDbLockRetry } from './cli-exec';
import { getDashboardSnapshot } from './dashboard';

function defaultSymbolsFromPreferences(preferences: {
  exchanges?: string[];
  regions?: string[];
}): string {
  const v1DefaultSymbols = 'AAPL,MSFT';
  if (process.env.AGENTIC_TRADER_WEBGUI_GLOBAL_SYMBOL_DEFAULTS !== '1') {
    return v1DefaultSymbols;
  }
  const exchanges = preferences.exchanges || [];
  const regions = preferences.regions || [];
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

function defaultSingleSymbol(data: Record<string, any>): string {
  return (
    data?.status?.state?.current_symbol ||
    data?.tradeContext?.record?.symbol ||
    data?.review?.record?.symbol ||
    defaultSymbolsFromPreferences(data?.preferences || {}).split(',')[0]
  );
}

function defaultRuntimeInterval(data: Record<string, any>): string {
  return (
    data?.status?.state?.interval ||
    data?.marketContext?.contextPack?.interval ||
    '1d'
  );
}

function defaultRuntimeLookback(data: Record<string, any>): string {
  return (
    data?.status?.state?.lookback ||
    data?.marketContext?.contextPack?.lookback ||
    '180d'
  );
}

function isTraderRunning(data: Record<string, any>): boolean {
  return (
    data?.status?.live_process === true &&
    data?.status?.runtime_state === 'active'
  );
}

export async function runRuntimeAction(kind: string): Promise<{
  message: string;
  dashboard: any;
}> {
  const data = await getDashboardSnapshot();

  if (kind === 'start') {
    if (isTraderRunning(data)) {
      return {
        message: `Runtime already active with PID ${data?.status?.state?.pid ?? '-'}.`,
        dashboard: data,
      };
    }
    const symbols = defaultSymbolsFromPreferences(data?.preferences || {});
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
      message: `Stop requested for PID ${data.status.state.pid}.`,
      dashboard: await getDashboardSnapshot(),
    };
  }

  if (kind === 'restart') {
    if ((data?.status?.state?.symbols || []).length) {
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
        message: `Runtime already active with PID ${data?.status?.state?.pid ?? '-'}. Stop it before running a one-shot cycle.`,
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
