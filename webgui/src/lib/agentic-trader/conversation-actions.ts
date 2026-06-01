/* eslint-disable @typescript-eslint/no-explicit-any -- CLI payloads are schema-loose JSON today */
import { execTrader } from './cli-exec';

export async function runInstruction(
  message: string,
  apply: boolean,
): Promise<any> {
  const args = ['instruct', '--json', '--message', message];
  if (apply) {
    args.push('--apply');
  }
  return execTrader(args, {
    expectJson: true,
    timeoutMs: 180_000,
  });
}

export async function runChat(persona: string, message: string): Promise<any> {
  return execTrader(
    ['chat', '--json', '--persona', persona, '--message', message],
    {
      expectJson: true,
      timeoutMs: 180_000,
    },
  );
}
