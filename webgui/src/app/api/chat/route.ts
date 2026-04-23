import { runChat } from '../../../lib/agentic-trader';

export const dynamic = 'force-dynamic';

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as {
      persona?: string;
      message?: string;
    };
    if (!body.message?.trim()) {
      return Response.json({ error: 'missing chat message' }, { status: 400 });
    }
    const result = await runChat(
      body.persona || 'operator_liaison',
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
