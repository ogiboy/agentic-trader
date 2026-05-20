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
 * Execute a supported runtime action specified by the request JSON body.
 *
 * Validates the request origin and JSON body, enforces a cooldown/single-flight guard, runs the requested action,
 * and returns the action result or an appropriate error response.
 *
 * @param request - Incoming HTTP request whose JSON body must be an object containing a string `kind` identifying the action.
 * @returns A Response with a JSON body: the runtime action result on success (200); `{ error: 'expected application/json' }` (400) if Content-Type is not JSON; `{ error: 'invalid json' }` (400) if the body is invalid or not an object; `{ error: 'invalid runtime action' }` (400) if `kind` is missing/invalid/unsupported; `{ error: 'forbidden origin' }` (403) if the origin/referer is not allowed; `{ error: <message> }` (500) for unexpected internal errors.
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
    return Response.json({ error: redactAndCapText(error) }, { status: 500 });
  }
}
