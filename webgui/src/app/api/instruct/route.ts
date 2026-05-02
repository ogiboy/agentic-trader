import {
  getDashboardSnapshot,
  runInstruction,
} from '../../../lib/agentic-trader';
import {
  beginRequestGuard,
  parseJsonObjectBody,
  redactAndCapText,
  rejectUnsafeWebguiRequest,
} from '../../../lib/http';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const MAX_INSTRUCTION_MESSAGE_LENGTH = 6_000;

/**
 * Handle same-origin JSON POST requests that run an instruction and return its result alongside the current dashboard snapshot.
 *
 * @param request - HTTP request whose JSON body must contain `message` (string). May include `apply` (boolean) to indicate whether the instruction should be applied.
 * @returns A Response whose JSON body is `{ result, dashboard }` on success. Malformed content type, bad JSON, foreign origins, or missing messages return structured 4xx JSON errors.
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
    if (
      typeof body.message !== 'string' ||
      !body.message.trim() ||
      (body.apply !== undefined && typeof body.apply !== 'boolean')
    ) {
      return Response.json({ error: 'invalid request' }, { status: 400 });
    }
    const message = body.message.trim();
    if (message.length > MAX_INSTRUCTION_MESSAGE_LENGTH) {
      return Response.json(
        { error: 'instruction message too large' },
        { status: 413 },
      );
    }
    const apply = body.apply === true;
    const guard = beginRequestGuard({
      key: 'instruct',
      cooldownMs: 1_500,
      singleFlight: true,
    });
    if (!guard.ok) {
      return guard.response;
    }
    try {
      const result = await runInstruction(message, apply);
      const dashboard = await getDashboardSnapshot();
      return Response.json({ result, dashboard });
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
