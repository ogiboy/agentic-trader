import {
  runProposalAction,
  type ProposalActionKind,
} from '../../../lib/agentic-trader';
import {
  beginRequestGuard,
  parseJsonObjectBody,
  redactAndCapText,
  rejectUnsafeWebguiRequest,
} from '../../../lib/http';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const SUPPORTED_PROPOSAL_ACTIONS = new Set<ProposalActionKind>([
  'approve',
  'reject',
  'reconcile',
]);

function isProposalActionKind(value: unknown): value is ProposalActionKind {
  return (
    typeof value === 'string' &&
    SUPPORTED_PROPOSAL_ACTIONS.has(value as ProposalActionKind)
  );
}

function stringField(value: unknown): string {
  return typeof value === 'string' ? value : '';
}

/**
 * Handle explicit manual-review proposal actions from the Web GUI.
 *
 * Supported actions are allowlisted and delegate to existing CLI proposal
 * commands. Approval still uses the configured broker adapter boundary; this
 * route does not construct orders or bypass terminal proposal-state guards.
 */
export async function POST(request: Request) {
  const unsafeResponse = rejectUnsafeWebguiRequest(request, {
    requireJson: true,
  });
  if (unsafeResponse) {
    return unsafeResponse;
  }

  const parsed = await parseJsonObjectBody(request, { maxBytes: 8 * 1024 });
  if (!parsed.ok) {
    return parsed.response;
  }
  const body = parsed.body;

  try {
    if (!isProposalActionKind(body.kind)) {
      return Response.json(
        { error: 'invalid proposal action' },
        { status: 400 },
      );
    }
    const proposalId = stringField(body.proposalId).trim();
    if (!proposalId) {
      return Response.json({ error: 'proposal id is required' }, { status: 400 });
    }
    const reviewNotes = stringField(body.reviewNotes).trim();
    if (body.kind === 'reject' && !reviewNotes) {
      return Response.json(
        { error: 'review note is required for reject' },
        { status: 400 },
      );
    }
    const guard = beginRequestGuard({
      key: 'proposals',
      cooldownMs: body.kind === 'approve' ? 3_000 : 1_500,
      singleFlight: true,
    });
    if (!guard.ok) {
      return guard.response;
    }
    try {
      const result = await runProposalAction(
        body.kind,
        proposalId,
        reviewNotes,
      );
      return Response.json(result);
    } finally {
      guard.release();
    }
  } catch (error) {
    return Response.json({ error: redactAndCapText(error) }, { status: 500 });
  }
}
