/* eslint-disable @typescript-eslint/no-explicit-any -- dashboard payloads are schema-loose JSON today */
import { formatList, formatTimestamp } from '../control-room.helpers';
import type { DashboardData, InstructionMode } from '../control-room.helpers';
import type { ControlRoomCopy } from './labels';
import { KeyValueList, Panel, TextList } from './primitives';

function instructionButtonLabel(
  busy: string | null,
  instructionMode: InstructionMode,
  copy: ControlRoomCopy,
) {
  if (busy === 'instruction') {
    return copy.common.working;
  }
  return instructionMode === 'apply'
    ? copy.settings.actions.apply
    : copy.settings.actions.preview;
}

export function SettingsView({
  copy,
  dashboard,
  instructionDraft,
  instructionMode,
  instructionResult,
  busy,
  onInstructionDraftChange,
  onInstructionModeChange,
  onSendInstruction,
}: Readonly<{
  copy: ControlRoomCopy;
  dashboard: DashboardData;
  instructionDraft: string;
  instructionMode: InstructionMode;
  instructionResult: Record<string, any> | null;
  busy: string | null;
  onInstructionDraftChange: (value: string) => void;
  onInstructionModeChange: (value: InstructionMode) => void;
  onSendInstruction: () => Promise<void>;
}>) {
  const recentRunLines = dashboard.recentRuns?.runs?.length
    ? dashboard.recentRuns.runs.map(
        (run: Record<string, any>) =>
          `${formatTimestamp(run.created_at)} | ${run.symbol} | ${run.interval} | ${copy.settings.fields.approved}=${run.approved}`,
      )
    : [copy.settings.recentRunsEmpty];
  const instructionLines = instructionResult
    ? [
        `${copy.settings.fields.instructionSummary}: ${instructionResult.instruction?.summary ?? '-'}`,
        `${copy.settings.fields.shouldUpdatePreferences}: ${instructionResult.instruction?.should_update_preferences ?? false}`,
        `${copy.settings.fields.requiresConfirmation}: ${instructionResult.instruction?.requires_confirmation ?? false}`,
        `${copy.settings.fields.applied}: ${
          instructionResult.applied ? copy.common.yes : copy.common.no
        }`,
        `${copy.settings.fields.instructionRationale}: ${instructionResult.instruction?.rationale ?? '-'}`,
      ]
    : [
        copy.settings.instructionEmpty,
        copy.settings.fields.instructionExamples,
        ...copy.settings.examples,
      ];

  return (
    <div className="grid grid--2">
      <Panel title={copy.settings.panels.preferences} accent="lime">
        <KeyValueList
          items={[
            [copy.settings.fields.regions, formatList(dashboard.preferences?.regions)],
            [
              copy.settings.fields.exchanges,
              formatList(dashboard.preferences?.exchanges),
            ],
            [
              copy.settings.fields.currencies,
              formatList(dashboard.preferences?.currencies),
            ],
            [copy.settings.fields.sectors, formatList(dashboard.preferences?.sectors)],
            [copy.settings.fields.risk, dashboard.preferences?.risk_profile ?? '-'],
            [copy.settings.fields.style, dashboard.preferences?.trade_style ?? '-'],
            [
              copy.settings.fields.behavior,
              dashboard.preferences?.behavior_preset ?? '-',
            ],
            [
              copy.settings.fields.agentProfile,
              dashboard.preferences?.agent_profile ?? '-',
            ],
            [copy.settings.fields.tone, dashboard.preferences?.agent_tone ?? '-'],
            [
              copy.settings.fields.strictness,
              dashboard.preferences?.strictness_preset ?? '-',
            ],
          ]}
        />
      </Panel>
      <Panel title={copy.settings.panels.recentRuns} accent="amber">
        <TextList items={recentRunLines} />
      </Panel>
      <Panel title={copy.settings.panels.operatorInstruction} accent="cyan">
        <TextList items={instructionLines} />
      </Panel>
      <Panel title={copy.settings.panels.composer} accent="rose">
        <div className="form-row">
          <label className="field-label">
            <span>{copy.settings.fields.mode}</span>
            <select
              value={instructionMode}
              onChange={(event) =>
                onInstructionModeChange(event.target.value as InstructionMode)
              }
            >
              <option value="preview">{copy.settings.modeOptions.preview}</option>
              <option value="apply">{copy.settings.modeOptions.apply}</option>
            </select>
          </label>
        </div>
        <div className="composer">
          <textarea
            value={instructionDraft}
            onChange={(event) => onInstructionDraftChange(event.target.value)}
            placeholder={copy.settings.placeholder}
          />
          <button
            className="button button--solid"
            disabled={busy === 'instruction'}
            onClick={() => void onSendInstruction()}
            type="button"
          >
            {instructionButtonLabel(busy, instructionMode, copy)}
          </button>
        </div>
      </Panel>
    </div>
  );
}
