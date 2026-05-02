import { runRuntimeAction } from '../../../lib/agentic-trader';
import {
  beginRequestGuard,
  parseJsonObjectBody,
  redactAndCapText,
  rejectUnsafeWebguiRequest,
} from '../../../lib/http';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const SUPPORTED_RUNTIME_ACTIONS = new Set([
  'start',
  'stop',
  'restart',
  'one-shot',
]);

function runtimeActionCooldownMs(kind: string): number {
  if (kind === 'stop') {
    return 1_000;
  }
  return 5_000;
}

/**
 * Handle POST requests that execute a supported runtime action specified in the request JSON.
 *
 * @param request - The incoming HTTP request whose JSON body must include a string `kind` identifying the action
 * @returns A Response with a JSON body:
 *          - the runtime action result (status 200) on success,
 *          - `{ error: 'expected application/json' }` (400) if the Content-Type is not JSON,
 *          - `{ error: 'invalid json' }` (400) if the body is not valid JSON or not an object,
 *          - `{ error: 'invalid runtime action' }` (400) if `kind` is missing, not a string, or not supported,
 *          - `{ error: 'forbidden origin' }` (403) if the request origin/referer is not same-origin,
 *          - `{ error: <message> }` (500) on unexpected internal errors.
 */
export async function POST(request: Request) {
  const unsafeResponse = rejectUnsafeWebguiRequest(request, {
    requireJson: true,
  });
  if (unsafeResponse) {
    return unsafeResponse;
  }

  const parsed = await parseJsonObjectBody(request, { maxBytes: 8 * 1024 });
  if (!parsed.ok) {
    return parsed.response;
  }
  const body = parsed.body;

  try {
    if (
      typeof body.kind !== 'string' ||
      !SUPPORTED_RUNTIME_ACTIONS.has(body.kind)
    ) {
      return Response.json(
        { error: 'invalid runtime action' },
        { status: 400 },
      );
    }
    const guard = beginRequestGuard({
      key: 'runtime',
      cooldownMs: runtimeActionCooldownMs(body.kind),
      singleFlight: true,
    });
    if (!guard.ok) {
      return guard.response;
    }
    try {
      const result = await runRuntimeAction(body.kind);
      return Response.json(result);
    } finally {
      guard.release();
    }
  } catch (error) {
    return Response.json(
      { error: redactAndCapText(error) },
      { status: 500 },
    );
  }
}
