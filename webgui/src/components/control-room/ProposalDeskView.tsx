import { CheckCircle2, RefreshCw, RotateCcw, XCircle } from 'lucide-react';
import { useTranslations } from 'next-intl';

import { Textarea } from '@/components/ui/textarea';
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
  proposalHeadlineWithCopy,
  proposalLines,
} from '../control-room.helpers';
import { useProposalContextCopy } from './intl-copy';
import { KeyValueList, Panel, TextList } from './Primitives';

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
  dashboard,
  busy,
  proposalNote,
  onProposalNoteChange,
  onProposalAction,
}: Readonly<{
  dashboard: DashboardData;
  busy: string | null;
  proposalNote: string;
  onProposalNoteChange: (value: string) => void;
  onProposalAction: (
    kind: ProposalActionKind,
    proposalId: string,
  ) => Promise<void>;
}>) {
  const common = useTranslations('controlRoom.common');
  const t = useTranslations('controlRoom.proposals');
  const contextCopy = useProposalContextCopy();
  const tradeProposals = asRecord(dashboard.tradeProposals);
  const proposals = asRecordArray(tradeProposals.proposals);
  const broker = asRecord(dashboard.broker);
  const proposalUnavailable = tradeProposals.available === false;
  const approvalBlockedReason = proposalApprovalBlockedReason(
    dashboard,
    contextCopy,
  );
  const hasProposalNote = Boolean(proposalNote.trim());

  return (
    <div className='grid grid--2'>
      <Panel title={t('panels.proposalDesk')} accent='amber'>
        <TextList items={proposalLines(dashboard, contextCopy)} />
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
                        <strong>
                          {proposalHeadlineWithCopy(proposal, contextCopy)}
                        </strong>
                        <span className='chip'>
                          {formatNumber(proposal.confidence, 2)}
                        </span>
                      </div>
                      <p>{asString(proposal.thesis)}</p>
                      <div className='proposal-card__meta'>
                        <span>{proposalId}</span>
                        <span>{asString(proposal.source)}</span>
                        <span>
                          {t('stopTake', {
                            stop: formatNumber(proposal.stop_loss, 2),
                            take: formatNumber(proposal.take_profit, 2),
                          })}
                        </span>
                      </div>
                      <div className='tool-actions'>
                        <button
                          className='button button--solid'
                          disabled={!canApprove || Boolean(busy)}
                          onClick={() =>
                            void onProposalAction('approve', proposalId)
                          }
                          title={t('actions.approve.title')}
                          type='button'
                        >
                          <CheckCircle2 aria-hidden size={16} />
                          {t('actions.approve.label')}
                        </button>
                        <button
                          className='button'
                          disabled={
                            !isPending || Boolean(busy) || !hasProposalNote
                          }
                          onClick={() =>
                            void onProposalAction('reject', proposalId)
                          }
                          title={t('actions.reject.title')}
                          type='button'
                        >
                          <XCircle aria-hidden size={16} />
                          {t('actions.reject.label')}
                        </button>
                        <button
                          className='button'
                          disabled={!canReconcile || Boolean(busy)}
                          onClick={() =>
                            void onProposalAction('reconcile', proposalId)
                          }
                          title={t('actions.reconcile.title')}
                          type='button'
                        >
                          <RotateCcw aria-hidden size={16} />
                          {t('actions.reconcile.label')}
                        </button>
                        <button
                          className='button'
                          disabled={!canRefresh || Boolean(busy)}
                          onClick={() =>
                            void onProposalAction('refresh', proposalId)
                          }
                          title={t('actions.refresh.title')}
                          type='button'
                        >
                          <RefreshCw aria-hidden size={16} />
                          {t('actions.refresh.label')}
                        </button>
                      </div>
                    </article>
                  );
                })}
              </div>
            ) : null}
            <div className='composer'>
              <Textarea
                onChange={(event) => onProposalNoteChange(event.target.value)}
                placeholder={t('notePlaceholder')}
                value={proposalNote}
              />
            </div>
          </>
        )}
      </Panel>
      <Panel title={t('panels.deskSafety')} accent='cyan'>
        <KeyValueList
          items={[
            [t('fields.backend'), asString(broker.backend)],
            [t('fields.state'), asString(broker.state)],
            [
              t('fields.externalPaper'),
              broker.external_paper ? common('yes') : common('no'),
            ],
            [
              t('fields.liveRequested'),
              broker.live_requested ? common('yes') : common('no'),
            ],
            [
              t('fields.killSwitch'),
              broker.kill_switch_active ? common('on') : common('off'),
            ],
            [t('fields.message'), asString(broker.message)],
          ]}
        />
      </Panel>
    </div>
  );
}
