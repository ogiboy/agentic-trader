import { runChat } from '../../../lib/agentic-trader';
import { isChatPersona } from '../../../lib/chat-personas';

export const dynamic = 'force-dynamic';

function isSameOriginRequest(request: Request): boolean {
  const requestOrigin = new URL(request.url).origin;
  const origin = request.headers.get('origin');
  if (origin) {
    return origin === requestOrigin;
  }
  const referer = request.headers.get('referer');
  if (!referer) {
    return true;
  }
  try {
    return new URL(referer).origin === requestOrigin;
  } catch {
    return false;
  }
}

/**
 * Handle same-origin JSON POST requests that run an operator chat workflow.
 *
 * @param request - HTTP request whose JSON body must include an optional `persona` and a `message` string; `message` must be non-empty after trimming
 * @returns A Response whose JSON is the chat result on success; malformed content type, bad JSON, foreign origins, invalid persona values, or missing messages return structured 4xx JSON errors
 */
export async function POST(request: Request) {
  const contentType = request.headers.get('content-type')?.toLowerCase() || '';
  if (!contentType.includes('application/json')) {
    return Response.json({ error: 'expected application/json' }, { status: 400 });
  }
  if (!isSameOriginRequest(request)) {
    return Response.json({ error: 'forbidden origin' }, { status: 403 });
  }

  let body: { persona?: string; message?: string };
  try {
    body = (await request.json()) as { persona?: string; message?: string };
  } catch {
    return Response.json({ error: 'invalid json' }, { status: 400 });
  }

  try {
    if (!body.message?.trim()) {
      return Response.json({ error: 'missing chat message' }, { status: 400 });
    }
    if (body.persona !== undefined && !isChatPersona(body.persona)) {
      return Response.json({ error: 'invalid persona' }, { status: 400 });
    }
    const result = await runChat(
      body.persona ?? 'operator_liaison',
      body.message,
    );
    return Response.json(result);
  } catch (error) {
    return Response.json(
      { error: error instanceof Error ? error.message : String(error) },
      { status: 500 },
    );
  }
}
