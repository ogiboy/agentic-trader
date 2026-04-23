import {
  getDashboardSnapshot,
  runInstruction,
} from '../../../lib/agentic-trader';

export const dynamic = 'force-dynamic';

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
    const result = await runInstruction(body.message, Boolean(body.apply));
    const dashboard = await getDashboardSnapshot();
    return Response.json({ result, dashboard });
  } catch (error) {
    return Response.json(
      { error: error instanceof Error ? error.message : String(error) },
      { status: 500 },
    );
  }
}
