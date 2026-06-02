import type { JsonRecord } from '../json-record';
import { execTrader } from './cli-exec';

export async function getDashboardSnapshot(): Promise<JsonRecord> {
  return (await execTrader(
    ['dashboard-snapshot', '--log-limit', '14', '--provider-check'],
    {
      expectJson: true,
      timeoutMs: 30_000,
    },
  )) as JsonRecord;
}
