import { runChat } from '../../../lib/agentic-trader';
import { isChatPersona } from '../../../lib/chat-personas';
import {
  beginRequestGuard,
  parseJsonObjectBody,
  redactAndCapText,
  rejectUnsafeWebguiRequest,
} from '../../../lib/http';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const MAX_CHAT_MESSAGE_LENGTH = 6_000;

/**
 * Handle same-origin JSON POST requests that run an operator chat workflow.
 *
 * @param request - HTTP request whose JSON body must include an optional `persona` and a `message` string; `message` must be non-empty after trimming
 * @returns A Response whose JSON is the chat result on success; malformed content type, bad JSON, foreign origins, invalid persona values, or missing messages return structured 4xx JSON errors
 */
export async function POST(request: Request) {
  const unsafeResponse = rejectUnsafeWebguiRequest(request, {
    requireJson: true,
  });
  if (unsafeResponse) {
    return unsafeResponse;
  }

  const parsed = await parseJsonObjectBody(request, { maxBytes: 16 * 1024 });
  if (!parsed.ok) {
    return parsed.response;
  }
  const body = parsed.body;

  try {
    if (typeof body.message !== 'string') {
      return Response.json({ error: 'invalid message' }, { status: 400 });
    }
    const message = body.message.trim();
    if (!message) {
      return Response.json({ error: 'missing chat message' }, { status: 400 });
    }
    if (message.length > MAX_CHAT_MESSAGE_LENGTH) {
      return Response.json({ error: 'chat message too large' }, { status: 413 });
    }
    const persona = body.persona;
    if (persona !== undefined && !isChatPersona(persona)) {
      return Response.json({ error: 'invalid persona' }, { status: 400 });
    }
    const guard = beginRequestGuard({
      key: 'chat',
      cooldownMs: 1_500,
      singleFlight: true,
    });
    if (!guard.ok) {
      return guard.response;
    }
    try {
      const result = await runChat(persona ?? 'operator_liaison', message);
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
