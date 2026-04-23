import { runChat } from '../../../lib/agentic-trader';
import { isChatPersona } from '../../../lib/chat-personas';

export const dynamic = 'force-dynamic';

/**
 * Handle POST requests to run a chat workflow using a JSON body.
 *
 * @param request - HTTP request whose JSON body must include an optional `persona` and a `message` string; `message` must be non-empty after trimming
 * @returns A Response whose JSON is the chat result on success; if `message` is missing or empty, a 400 JSON `{ error: 'missing chat message' }`; on unexpected errors, a 500 JSON `{ error: <message> }`
 */
export async function POST(request: Request) {
  try {
    const body = (await request.json()) as {
      persona?: string;
      message?: string;
    };
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
