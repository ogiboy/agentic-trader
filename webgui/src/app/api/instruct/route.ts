import {
  getDashboardSnapshot,
  runInstruction,
} from '../../../lib/agentic-trader';

export const dynamic = 'force-dynamic';

/**
 * Handle POST requests that run an instruction and return its result alongside the current dashboard snapshot.
 *
 * @param request - HTTP request whose JSON body must contain `message` (string). May include `apply` (boolean) to indicate whether the instruction should be applied.
 * @returns A Response whose JSON body is `{ result, dashboard }` on success. If `message` is missing or empty the response is `{ error: 'missing instruction message' }` with status 400. On other errors the response is `{ error: <message> }` with status 500.
 */
export async function POST(request: Request) {
  try {
    const body = (await request.json()) as {
      message?: string;
      apply?: boolean;
    };
    if (!body.message?.trim()) {
      return Response.json(
        { error: 'missing instruction message' },
        { status: 400 },
      );
    }
    const apply = body.apply === true;
    const result = await runInstruction(body.message, apply);
    const dashboard = await getDashboardSnapshot();
    return Response.json({ result, dashboard });
  } catch (error) {
    return Response.json(
      { error: error instanceof Error ? error.message : String(error) },
      { status: 500 },
    );
  }
}
