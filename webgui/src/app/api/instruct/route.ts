import {
  getDashboardSnapshot,
  runInstruction,
} from '../../../lib/agentic-trader';
import { parseJsonObjectBody } from '../../../lib/http';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const SAFE_METHODS_WITHOUT_BROWSER_ORIGIN = new Set(['GET', 'HEAD', 'OPTIONS']);

function isSameOriginRequest(request: Request): boolean {
  const requestOrigin = new URL(request.url).origin;
  const origin = request.headers.get('origin');
  if (origin) {
    return origin === requestOrigin;
  }
  const referer = request.headers.get('referer');
  if (!referer) {
    return SAFE_METHODS_WITHOUT_BROWSER_ORIGIN.has(
      request.method.toUpperCase(),
    );
  }
  try {
    return new URL(referer).origin === requestOrigin;
  } catch {
    return false;
  }
}

/**
 * Handle same-origin JSON POST requests that run an instruction and return its result alongside the current dashboard snapshot.
 *
 * @param request - HTTP request whose JSON body must contain `message` (string). May include `apply` (boolean) to indicate whether the instruction should be applied.
 * @returns A Response whose JSON body is `{ result, dashboard }` on success. Malformed content type, bad JSON, foreign origins, or missing messages return structured 4xx JSON errors.
 */
export async function POST(request: Request) {
  const contentType = request.headers.get('content-type')?.toLowerCase() || '';
  if (!contentType.includes('application/json')) {
    return Response.json(
      { error: 'expected application/json' },
      { status: 400 },
    );
  }
  if (!isSameOriginRequest(request)) {
    return Response.json({ error: 'forbidden origin' }, { status: 403 });
  }

  const parsed = await parseJsonObjectBody(request);
  if (!parsed.ok) {
    return parsed.response;
  }
  const body = parsed.body;

  try {
    if (
      typeof body.message !== 'string' ||
      !body.message.trim() ||
      (body.apply !== undefined && typeof body.apply !== 'boolean')
    ) {
      return Response.json({ error: 'invalid request' }, { status: 400 });
    }
    const message = body.message.trim();
    const apply = body.apply === true;
    const result = await runInstruction(message, apply);
    const dashboard = await getDashboardSnapshot();
    return Response.json({ result, dashboard });
  } catch (error) {
    return Response.json(
      { error: error instanceof Error ? error.message : String(error) },
      { status: 500 },
    );
  }
}
