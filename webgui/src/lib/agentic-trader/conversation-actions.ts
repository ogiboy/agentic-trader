import type { JsonRecord } from '../json-record';
import { execTrader } from './cli-exec';

export async function runInstruction(
  message: string,
  apply: boolean,
): Promise<JsonRecord> {
  const args = ['instruct', '--json', '--message', message];
  if (apply) {
    args.push('--apply');
  }
  return (await execTrader(args, {
    expectJson: true,
    timeoutMs: 180_000,
  })) as JsonRecord;
}

export async function runChat(
  persona: string,
  message: string,
): Promise<JsonRecord> {
  return (await execTrader(
    ['chat', '--json', '--persona', persona, '--message', message],
    {
      expectJson: true,
      timeoutMs: 180_000,
    },
  )) as JsonRecord;
}
