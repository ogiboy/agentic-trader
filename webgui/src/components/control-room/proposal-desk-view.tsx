import { CheckCircle2, RefreshCw, RotateCcw, XCircle } from 'lucide-react';

import type {
  DashboardData,
  ProposalActionKind,
} from '../control-room.helpers';
import {
  asRecord,
  asRecordArray,
  asString,
  formatNumber,
  proposalApprovalBlockedReason,
  proposalHeadline,
  proposalLines,
} from '../control-room.helpers';
import type { ControlRoomCopy } from './labels';
import { KeyValueList, Panel, TextList } from './primitives';

/**
 * Render the Proposal Desk panel with proposal cards, a review-note composer, and safety metadata.
 *
 * The panel lists up to six proposals and exposes action buttons for approve, reject, reconcile, and refresh.
 * Action buttons are enabled only when the proposal's status and required metadata allow it and a non-empty
 * review note is present where the UI requires one.
 *
 * @param dashboard - Full dashboard payload used to derive proposals, availability flags, and broker safety fields
 * @param busy - Current busy token that disables interactive buttons when non-null
 * @param proposalNote - Current text of the review note composer; trimmed emptiness gates certain actions
 * @param onProposalNoteChange - Called with the updated proposal note when the composer textarea changes
 * @param onProposalAction - Invoked to perform a proposal action; receives the action kind and the target proposal ID
 * @returns The Proposal Desk React element
 */
export function ProposalDeskView({
  copy,
  dashboard,
  busy,
  proposalNote,
  onProposalNoteChange,
  onProposalAction,
}: Readonly<{
  copy: ControlRoomCopy;
  dashboard: DashboardData;
  busy: string | null;
  proposalNote: string;
  onProposalNoteChange: (value: string) => void;
  onProposalAction: (
    kind: ProposalActionKind,
    proposalId: string,
  ) => Promise<void>;
}>) {
  const tradeProposals = asRecord(dashboard.tradeProposals);
  const proposals = asRecordArray(tradeProposals.proposals);
  const broker = asRecord(dashboard.broker);
  const proposalUnavailable = tradeProposals.available === false;
  const approvalBlockedReason = proposalApprovalBlockedReason(dashboard);
  const hasProposalNote = Boolean(proposalNote.trim());

  return (
    <div className='grid grid--2'>
      <Panel title={copy.proposals.panels.proposalDesk} accent='amber'>
        <TextList items={proposalLines(dashboard)} />
        {approvalBlockedReason ? (
          <div className='banner banner--warn'>{approvalBlockedReason}</div>
        ) : null}
        {proposalUnavailable ? null : (
          <>
            {proposals.length ? (
              <div className='proposal-list'>
                {proposals.slice(0, 6).map((proposal) => {
                  const proposalId = asString(proposal.proposal_id, '');
                  const status = asString(proposal.status, '');
                  const isPending = status === 'pending';
                  const canApprove =
                    isPending && !approvalBlockedReason && hasProposalNote;
                  const canReconcile =
                    status === 'approved' &&
                    Boolean(proposal.execution_intent_id) &&
                    hasProposalNote;
                  const canRefresh =
                    (status === 'approved' || status === 'executed') &&
                    proposal.execution_outcome_status === 'accepted' &&
                    Boolean(proposal.execution_order_id) &&
                    hasProposalNote;
                  return (
                    <article className='proposal-card' key={proposalId}>
                      <div className='proposal-card__head'>
                        <strong>{proposalHeadline(proposal)}</strong>
                        <span className='chip'>
                          {formatNumber(proposal.confidence, 2)}
                        </span>
                      </div>
                      <p>{asString(proposal.thesis)}</p>
                      <div className='proposal-card__meta'>
                        <span>{proposalId}</span>
                        <span>{asString(proposal.source)}</span>
                        <span>
                          {copy.proposals.stopTake(
                            formatNumber(proposal.stop_loss, 2),
                            formatNumber(proposal.take_profit, 2),
                          )}
                        </span>
                      </div>
                      <div className='tool-actions'>
                        <button
                          className='button button--solid'
                          disabled={!canApprove || Boolean(busy)}
                          onClick={() =>
                            void onProposalAction('approve', proposalId)
                          }
                          title={copy.proposals.actions.approve.title}
                          type='button'
                        >
                          <CheckCircle2 aria-hidden size={16} />
                          {copy.proposals.actions.approve.label}
                        </button>
                        <button
                          className='button'
                          disabled={
                            !isPending || Boolean(busy) || !hasProposalNote
                          }
                          onClick={() =>
                            void onProposalAction('reject', proposalId)
                          }
                          title={copy.proposals.actions.reject.title}
                          type='button'
                        >
                          <XCircle aria-hidden size={16} />
                          {copy.proposals.actions.reject.label}
                        </button>
                        <button
                          className='button'
                          disabled={!canReconcile || Boolean(busy)}
                          onClick={() =>
                            void onProposalAction('reconcile', proposalId)
                          }
                          title={copy.proposals.actions.reconcile.title}
                          type='button'
                        >
                          <RotateCcw aria-hidden size={16} />
                          {copy.proposals.actions.reconcile.label}
                        </button>
                        <button
                          className='button'
                          disabled={!canRefresh || Boolean(busy)}
                          onClick={() =>
                            void onProposalAction('refresh', proposalId)
                          }
                          title={copy.proposals.actions.refresh.title}
                          type='button'
                        >
                          <RefreshCw aria-hidden size={16} />
                          {copy.proposals.actions.refresh.label}
                        </button>
                      </div>
                    </article>
                  );
                })}
              </div>
            ) : null}
            <div className='composer'>
              <textarea
                onChange={(event) => onProposalNoteChange(event.target.value)}
                placeholder={copy.proposals.notePlaceholder}
                value={proposalNote}
              />
            </div>
          </>
        )}
      </Panel>
      <Panel title={copy.proposals.panels.deskSafety} accent='cyan'>
        <KeyValueList
          items={[
            [copy.proposals.fields.backend, asString(broker.backend)],
            [copy.proposals.fields.state, asString(broker.state)],
            [
              copy.proposals.fields.externalPaper,
              broker.external_paper
                ? copy.common.yes
                : copy.common.no,
            ],
            [
              copy.proposals.fields.liveRequested,
              broker.live_requested
                ? copy.common.yes
                : copy.common.no,
            ],
            [
              copy.proposals.fields.killSwitch,
              broker.kill_switch_active
                ? copy.common.on
                : copy.common.off,
            ],
            [copy.proposals.fields.message, asString(broker.message)],
          ]}
        />
      </Panel>
    </div>
  );
}
