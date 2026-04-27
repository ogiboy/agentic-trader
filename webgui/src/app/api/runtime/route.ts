import { runRuntimeAction } from '../../../lib/agentic-trader';

export const runtime = 'nodejs';
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
  const contentType = request.headers.get('content-type')?.toLowerCase() || '';
  if (!contentType.includes('application/json')) {
    return Response.json({ error: 'expected application/json' }, { status: 400 });
  }
  if (!isSameOriginRequest(request)) {
    return Response.json({ error: 'forbidden origin' }, { status: 403 });
  }

  let body: { kind?: unknown };
  try {
    const parsed: unknown = await request.json();
    if (typeof parsed !== 'object' || parsed === null) {
      return Response.json({ error: 'invalid json' }, { status: 400 });
    }
    body = parsed as { kind?: unknown };
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
