import { useTranslations } from 'next-intl';

import type {
  DashboardData,
  InstructionMode,
  InstructionResult,
} from '../control-room.helpers';
import {
  asRecord,
  asRecordArray,
  asString,
  formatList,
  formatTimestamp,
} from '../control-room.helpers';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { KeyValueList, Panel, TextList } from './Primitives';

function instructionButtonLabel(
  busy: string | null,
  instructionMode: InstructionMode,
  labels: Readonly<{
    apply: string;
    preview: string;
    working: string;
  }>,
) {
  if (busy === 'instruction') {
    return labels.working;
  }
  return instructionMode === 'apply' ? labels.apply : labels.preview;
}

export function SettingsView({
  dashboard,
  instructionDraft,
  instructionMode,
  instructionResult,
  busy,
  onInstructionDraftChange,
  onInstructionModeChange,
  onSendInstruction,
}: Readonly<{
  dashboard: DashboardData;
  instructionDraft: string;
  instructionMode: InstructionMode;
  instructionResult: InstructionResult | null;
  busy: string | null;
  onInstructionDraftChange: (value: string) => void;
  onInstructionModeChange: (value: InstructionMode) => void;
  onSendInstruction: () => Promise<void>;
}>) {
  const common = useTranslations('controlRoom.common');
  const t = useTranslations('controlRoom.settings');
  const recentRuns = asRecord(dashboard.recentRuns);
  const preferences = asRecord(dashboard.preferences);
  const instruction = asRecord(instructionResult?.instruction);
  const recentRunRows = asRecordArray(recentRuns.runs);
  const recentRunLines = recentRunRows.length
    ? recentRunRows.map(
        (run) =>
          `${formatTimestamp(run.created_at)} | ${asString(run.symbol)} | ${asString(run.interval)} | ${t('fields.approved')}=${asString(run.approved)}`,
      )
    : [t('recentRunsEmpty')];
  const instructionLines = instructionResult
    ? [
        `${t('fields.instructionSummary')}: ${asString(instruction.summary)}`,
        `${t('fields.shouldUpdatePreferences')}: ${asString(instruction.should_update_preferences, 'false')}`,
        `${t('fields.requiresConfirmation')}: ${asString(instruction.requires_confirmation, 'false')}`,
        `${t('fields.applied')}: ${
          instructionResult.applied ? common('yes') : common('no')
        }`,
        `${t('fields.instructionRationale')}: ${asString(instruction.rationale)}`,
      ]
    : [
        t('instructionEmpty'),
        t('fields.instructionExamples'),
        t('examples.conservative'),
        t('examples.capitalPreservation'),
      ];

  return (
    <div className='grid grid--2'>
      <Panel title={t('panels.preferences')} accent='lime'>
        <KeyValueList
          items={[
            [t('fields.regions'), formatList(preferences.regions)],
            [t('fields.exchanges'), formatList(preferences.exchanges)],
            [t('fields.currencies'), formatList(preferences.currencies)],
            [t('fields.sectors'), formatList(preferences.sectors)],
            [t('fields.risk'), asString(preferences.risk_profile)],
            [t('fields.style'), asString(preferences.trade_style)],
            [t('fields.behavior'), asString(preferences.behavior_preset)],
            [t('fields.agentProfile'), asString(preferences.agent_profile)],
            [t('fields.tone'), asString(preferences.agent_tone)],
            [t('fields.strictness'), asString(preferences.strictness_preset)],
          ]}
        />
      </Panel>
      <Panel title={t('panels.recentRuns')} accent='amber'>
        <TextList items={recentRunLines} />
      </Panel>
      <Panel title={t('panels.operatorInstruction')} accent='cyan'>
        <TextList items={instructionLines} />
      </Panel>
      <Panel title={t('panels.composer')} accent='rose'>
        <div className='form-row'>
          <div className='field-label'>
            <span>{t('fields.mode')}</span>
            <Select
              value={instructionMode}
              onValueChange={(value) =>
                onInstructionModeChange(value as InstructionMode)
              }
            >
              <SelectTrigger
                aria-label={t('fields.mode')}
                className='field-select'
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value='preview'>
                  {t('modeOptions.preview')}
                </SelectItem>
                <SelectItem value='apply'>{t('modeOptions.apply')}</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <div className='composer'>
          <Textarea
            value={instructionDraft}
            onChange={(event) => onInstructionDraftChange(event.target.value)}
            placeholder={t('placeholder')}
          />
          <button
            className='button button--solid'
            disabled={busy === 'instruction'}
            onClick={() => void onSendInstruction()}
            type='button'
          >
            {instructionButtonLabel(busy, instructionMode, {
              apply: t('actions.apply'),
              preview: t('actions.preview'),
              working: common('working'),
            })}
          </button>
        </div>
      </Panel>
    </div>
  );
}
