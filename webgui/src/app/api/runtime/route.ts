import { runRuntimeAction } from '../../../lib/agentic-trader';

export const dynamic = 'force-dynamic';

const SUPPORTED_RUNTIME_ACTIONS = new Set([
  'start',
  'stop',
  'restart',
  'one-shot',
]);
const SAFE_METHODS_WITHOUT_BROWSER_ORIGIN = new Set(['GET', 'HEAD', 'OPTIONS']);

function isSameOriginRequest(request: Request): boolean {
  const requestOrigin = new URL(request.url).origin;
  const origin = request.headers.get('origin');
  if (origin) {
    return origin === requestOrigin;
  }
  const referer = request.headers.get('referer');
  if (!referer) {
    return SAFE_METHODS_WITHOUT_BROWSER_ORIGIN.has(request.method.toUpperCase());
  }
  try {
    return new URL(referer).origin === requestOrigin;
  } catch {
    return false;
  }
}

/**
 * Handle POST requests to execute a runtime action and return the result as JSON.
 *
 * Expects the request body to be JSON with a `kind` string. If `kind` is missing,
 * responds with a 400 JSON error. On success returns the runtime action result
 * as JSON. On unexpected errors responds with a 500 JSON error containing the
 * error message.
 *
 * @param request - The incoming HTTP request whose JSON body should include `kind`
 * @returns A Response with a JSON body:
 *          - the runtime action result and status 200 on success,
 *          - `{ error: 'missing runtime action' }` with status 400 if `kind` is absent,
 *          - `{ error: <message> }` with status 500 on failure.
 */
export async function POST(request: Request) {
  const contentType = request.headers.get('content-type')?.toLowerCase() || '';
  if (!contentType.includes('application/json')) {
    return Response.json({ error: 'expected application/json' }, { status: 400 });
  }
  if (!isSameOriginRequest(request)) {
    return Response.json({ error: 'forbidden origin' }, { status: 403 });
  }

  let body: { kind?: unknown };
  try {
    body = (await request.json()) as { kind?: unknown };
  } catch {
    return Response.json({ error: 'invalid json' }, { status: 400 });
  }

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
    const result = await runRuntimeAction(body.kind);
    return Response.json(result);
  } catch (error) {
    return Response.json(
      { error: error instanceof Error ? error.message : String(error) },
      { status: 500 },
    );
  }
}
