import { getDashboardSnapshot } from '../../../lib/agentic-trader';

export const dynamic = 'force-dynamic';

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
