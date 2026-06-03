import { useTranslations } from 'next-intl';

import type { DashboardData } from '../control-room.helpers';
import
  {
    asRecord,
    asRecordArray,
    asString,
    formatTimestamp,
  } from '../control-room.helpers';
import { KeyValueList, Panel, TextList } from './primitives';

export function RuntimeView({
  dashboard,
}: Readonly<{ dashboard: DashboardData }>) {
  const common = useTranslations('controlRoom.common');
  const t = useTranslations('controlRoom.runtime');
  const status = asRecord(dashboard.status);
  const state = asRecord(status.state);
  const agentActivity = asRecord(dashboard.agentActivity);
  const supervisor = asRecord(dashboard.supervisor);
  const runtimeEventRows = asRecordArray(dashboard.logs);
  const stageStatusRows = asRecordArray(agentActivity.stage_statuses);
  const stderrTail = Array.isArray(supervisor.stderr_tail)
    ? supervisor.stderr_tail.map((item) => asString(item))
    : [];
  const stdoutTail = Array.isArray(supervisor.stdout_tail)
    ? supervisor.stdout_tail.map((item) => asString(item))
    : [];
  const runtimeEvents = runtimeEventRows.length
    ? runtimeEventRows.map(
        (event) =>
          `${formatTimestamp(event.created_at)} | ${asString(event.level)} | ${asString(event.event_type)} | ${asString(event.symbol)} | ${asString(event.message)}`,
      )
    : [t('empty.events')];
  const supervisorTails = [
    ...(stderrTail.length ? stderrTail : [t('empty.stderr')]),
    ...(stdoutTail.length ? stdoutTail : [t('empty.stdout')]),
  ];

  return (
    <div className='grid grid--2'>
      <Panel title={t('panels.state')} accent='lime'>
        <KeyValueList
          items={[
            [
              t('fields.runtime'),
              asString(status.runtime_state),
            ],
            [
              t('fields.liveProcess'),
              status.live_process ? common('yes') : common('no'),
            ],
            [
              t('fields.pid'),
              asString(state.pid),
            ],
            [
              t('fields.currentSymbol'),
              asString(state.current_symbol),
            ],
            [
              t('fields.cycleCount'),
              asString(state.cycle_count),
            ],
            [
              t('fields.updated'),
              formatTimestamp(state.updated_at),
            ],
            [
              t('fields.stopRequested'),
              asString(state.stop_requested, 'false'),
            ],
            [
              t('fields.status'),
              asString(status.status_message),
            ],
          ]}
        />
      </Panel>
      <Panel title={t('panels.stageFlow')} accent='cyan'>
        <TextList
          items={stageStatusRows.map(
            (stage) =>
              `${asString(stage.stage)} | ${asString(stage.status)} | ${asString(stage.message)}`,
          )}
        />
      </Panel>
      <Panel title={t('panels.events')} accent='amber'>
        <TextList items={runtimeEvents} />
      </Panel>
      <Panel title={t('panels.supervisorTails')} accent='rose'>
        <TextList items={supervisorTails} />
      </Panel>
    </div>
  );
}
