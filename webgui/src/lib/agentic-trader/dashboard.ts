/* eslint-disable @typescript-eslint/no-explicit-any -- Dashboard payloads are schema-loose JSON today */
import { execTrader } from './cli-exec';

export async function getDashboardSnapshot(): Promise<any> {
  return execTrader(
    ['dashboard-snapshot', '--log-limit', '14', '--provider-check'],
    {
      expectJson: true,
      timeoutMs: 30_000,
    },
  );
}
