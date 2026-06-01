/* eslint-disable @typescript-eslint/no-explicit-any -- Proposal payloads are schema-loose JSON today */
import { execTraderWithDbLockRetry } from './cli-exec';
import { getDashboardSnapshot } from './dashboard';

export type ProposalActionKind = 'approve' | 'reject' | 'reconcile' | 'refresh';

function proposalActionMessage(kind: ProposalActionKind, result: any): string {
  const proposal = result?.proposal || result;
  const symbol = proposal?.symbol || 'Proposal';
  const status = proposal?.status || kind;
  if (kind === 'approve') {
    const outcome =
      result?.outcome?.status || proposal?.execution_outcome_status || '-';
    return `${symbol} proposal approved; proposal=${status}, broker=${outcome}.`;
  }
  if (kind === 'reject') {
    return `${symbol} proposal rejected.`;
  }
  if (kind === 'refresh') {
    const outcome =
      result?.outcome?.status || proposal?.execution_outcome_status || '-';
    return `${symbol} proposal refreshed; proposal=${status}, broker=${outcome}.`;
  }
  return `${symbol} proposal reconciled; status=${status}.`;
}

export async function runProposalAction(
  kind: ProposalActionKind,
  proposalId: string,
  reviewNotes = '',
): Promise<{
  message: string;
  dashboard: any;
  result: any;
}> {
  const cleanProposalId = proposalId.trim();
  const cleanNotes = reviewNotes.trim();
  if (!cleanProposalId) {
    throw new Error('Proposal id is required.');
  }
  if (!cleanNotes) {
    throw new Error(`Review note is required for ${kind}.`);
  }

  let result: any;
  if (kind === 'approve') {
    result = await execTraderWithDbLockRetry(
      [
        'proposal-approve',
        cleanProposalId,
        '--review-notes',
        cleanNotes,
        '--json',
      ],
      { expectJson: true, timeoutMs: 90_000 },
    );
  } else if (kind === 'reject') {
    result = await execTraderWithDbLockRetry(
      ['proposal-reject', cleanProposalId, '--reason', cleanNotes, '--json'],
      { expectJson: true, timeoutMs: 45_000 },
    );
  } else if (kind === 'reconcile') {
    result = await execTraderWithDbLockRetry(
      [
        'proposal-reconcile',
        cleanProposalId,
        '--review-notes',
        cleanNotes,
        '--json',
      ],
      { expectJson: true, timeoutMs: 45_000 },
    );
  } else if (kind === 'refresh') {
    result = await execTraderWithDbLockRetry(
      [
        'proposal-refresh',
        cleanProposalId,
        '--review-notes',
        cleanNotes,
        '--json',
      ],
      { expectJson: true, timeoutMs: 45_000 },
    );
  } else {
    throw new Error(`Unsupported proposal action: ${kind}`);
  }

  return {
    dashboard: await getDashboardSnapshot(),
    message: proposalActionMessage(kind, result),
    result,
  };
}
