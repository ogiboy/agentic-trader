import { getDashboardSnapshot } from '../../../lib/agentic-trader';
import {
  redactAndCapText,
  rejectUnsafeWebguiRequest,
} from '../../../lib/http';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

/**
 * Handle GET requests for the dashboard endpoint and return a dashboard snapshot.
 *
 * @returns A Response whose JSON body is the dashboard snapshot on success; on failure the JSON body is `{ error: string }` and the response status is `500`. The `error` string is the thrown Error's `message` when available, otherwise `String(error)`.
 */
export async function GET(request: Request) {
  const unsafeResponse = rejectUnsafeWebguiRequest(request, {
    requireJson: false,
  });
  if (unsafeResponse) {
    return unsafeResponse;
  }
  try {
    const dashboard = await getDashboardSnapshot();
    return Response.json(dashboard);
  } catch (error) {
    return Response.json(
      { error: redactAndCapText(error) },
      { status: 500 },
    );
  }
}
