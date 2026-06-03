export function accountCurrency(data) {
  return (
    data.financeOps?.accounting?.currency ||
    data.portfolio?.accounting?.currency ||
    data.preferences?.currencies?.[0] ||
    'USD'
  );
}

export function defaultSymbolsFromPreferences(preferences) {
  const exchanges = preferences?.exchanges || [];
  const regions = preferences?.regions || [];
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
  return 'BTC-USD,ETH-USD';
}

export function defaultSingleSymbol(data) {
  return (
    data?.status?.state?.current_symbol ||
    data?.tradeContext?.record?.symbol ||
    data?.review?.record?.symbol ||
    defaultSymbolsFromPreferences(data?.preferences).split(',')[0]
  );
}

export function defaultRuntimeInterval(data) {
  return (
    data?.status?.state?.interval ||
    data?.marketContext?.contextPack?.interval ||
    '1d'
  );
}

export function defaultRuntimeLookback(data) {
  return (
    data?.status?.state?.lookback ||
    data?.marketContext?.contextPack?.lookback ||
    '180d'
  );
}

export function getSupervisorLogLines(supervisor) {
  if (supervisor?.stderr_tail?.length) {
    return ['stderr:', ...supervisor.stderr_tail.slice(-3)];
  }
  if (supervisor?.stdout_tail?.length) {
    return ['stdout:', ...supervisor.stdout_tail.slice(-3)];
  }
  return ['No daemon log tail yet.'];
}
