import { getDashboardSnapshot } from '../../../lib/agentic-trader';

export const dynamic = 'force-dynamic';

/**
 * Handle GET requests for the dashboard endpoint and return a dashboard snapshot.
 *
 * @returns A Response whose JSON body is the dashboard snapshot on success; on failure the JSON body is `{ error: string }` and the response status is `500`. The `error` string is the thrown Error's `message` when available, otherwise `String(error)`.
 */
export async function GET() {
  try {
    const dashboard = await getDashboardSnapshot();
    return Response.json(dashboard);
  } catch (error) {
    return Response.json(
      { error: error instanceof Error ? error.message : String(error) },
      { status: 500 },
    );
  }
}
