import { runRuntimeAction } from '../../../lib/agentic-trader';

export const dynamic = 'force-dynamic';

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
