import { asRecord, asString, type JsonRecord } from '../json-record';
import { execTraderWithDbLockRetry } from './cli-exec';
import { getDashboardSnapshot } from './dashboard';

export type ProposalActionKind = 'approve' | 'reject' | 'reconcile' | 'refresh';

function proposalActionMessage(
  kind: ProposalActionKind,
  result: JsonRecord,
): string {
  const proposal = asRecord(result.proposal);
  const messageSource = Object.keys(proposal).length ? proposal : result;
  const outcome = asRecord(result.outcome);
  const symbol = asString(messageSource.symbol, 'Proposal');
  const status = asString(messageSource.status, kind);
  if (kind === 'approve') {
    const brokerStatus = asString(
      outcome.status,
      asString(messageSource.execution_outcome_status),
    );
    return `${symbol} proposal approved; proposal=${status}, broker=${brokerStatus}.`;
  }
  if (kind === 'reject') {
    return `${symbol} proposal rejected.`;
  }
  if (kind === 'refresh') {
    const brokerStatus = asString(
      outcome.status,
      asString(messageSource.execution_outcome_status),
    );
    return `${symbol} proposal refreshed; proposal=${status}, broker=${brokerStatus}.`;
  }
  return `${symbol} proposal reconciled; status=${status}.`;
}

export async function runProposalAction(
  kind: ProposalActionKind,
  proposalId: string,
  reviewNotes = '',
): Promise<{
  message: string;
  dashboard: JsonRecord;
  result: JsonRecord;
}> {
  const cleanProposalId = proposalId.trim();
  const cleanNotes = reviewNotes.trim();
  if (!cleanProposalId) {
    throw new Error('Proposal id is required.');
  }
  if (!cleanNotes) {
    throw new Error(`Review note is required for ${kind}.`);
  }

  let result: JsonRecord;
  if (kind === 'approve') {
    result = (await execTraderWithDbLockRetry(
      [
        'proposal-approve',
        cleanProposalId,
        '--review-notes',
        cleanNotes,
        '--json',
      ],
      { expectJson: true, timeoutMs: 90_000 },
    )) as JsonRecord;
  } else if (kind === 'reject') {
    result = (await execTraderWithDbLockRetry(
      ['proposal-reject', cleanProposalId, '--reason', cleanNotes, '--json'],
      { expectJson: true, timeoutMs: 45_000 },
    )) as JsonRecord;
  } else if (kind === 'reconcile') {
    result = (await execTraderWithDbLockRetry(
      [
        'proposal-reconcile',
        cleanProposalId,
        '--review-notes',
        cleanNotes,
        '--json',
      ],
      { expectJson: true, timeoutMs: 45_000 },
    )) as JsonRecord;
  } else if (kind === 'refresh') {
    result = (await execTraderWithDbLockRetry(
      [
        'proposal-refresh',
        cleanProposalId,
        '--review-notes',
        cleanNotes,
        '--json',
      ],
      { expectJson: true, timeoutMs: 45_000 },
    )) as JsonRecord;
  } else {
    throw new Error(`Unsupported proposal action: ${kind}`);
  }

  return {
    dashboard: await getDashboardSnapshot(),
    message: proposalActionMessage(kind, result),
    result,
  };
}
