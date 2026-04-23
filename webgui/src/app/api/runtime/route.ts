import { runRuntimeAction } from '../../../lib/agentic-trader';

export const dynamic = 'force-dynamic';

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
  try {
    const body = (await request.json()) as { kind?: string };
    if (!body.kind) {
      return Response.json(
        { error: 'missing runtime action' },
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
