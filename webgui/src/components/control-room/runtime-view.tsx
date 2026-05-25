import type { DashboardData } from '../control-room.helpers';
import { formatTimestamp } from '../control-room.helpers';
import type { ControlRoomCopy } from './labels';
import { KeyValueList, Panel, TextList } from './primitives';

export function RuntimeView({
  copy,
  dashboard,
}: Readonly<{ copy: ControlRoomCopy; dashboard: DashboardData }>) {
  const runtimeEvents = dashboard.logs?.length
    ? dashboard.logs.map(
        (event: Record<string, string>) =>
          `${formatTimestamp(event.created_at)} | ${event.level} | ${event.event_type} | ${event.symbol ?? '-'} | ${event.message}`,
      )
    : [copy.runtime.empty.events];
  const supervisorTails = [
    ...(dashboard.supervisor?.stderr_tail?.length
      ? dashboard.supervisor.stderr_tail
      : [copy.runtime.empty.stderr]),
    ...(dashboard.supervisor?.stdout_tail?.length
      ? dashboard.supervisor.stdout_tail
      : [copy.runtime.empty.stdout]),
  ];

  return (
    <div className='grid grid--2'>
      <Panel title={copy.runtime.panels.state} accent='lime'>
        <KeyValueList
          items={[
            [
              copy.runtime.fields.runtime,
              dashboard.status?.runtime_state ?? '-',
            ],
            [
              copy.runtime.fields.liveProcess,
              dashboard.status?.live_process ? copy.common.yes : copy.common.no,
            ],
            [
              copy.runtime.fields.pid,
              String(dashboard.status?.state?.pid ?? '-'),
            ],
            [
              copy.runtime.fields.currentSymbol,
              dashboard.status?.state?.current_symbol ?? '-',
            ],
            [
              copy.runtime.fields.cycleCount,
              String(dashboard.status?.state?.cycle_count ?? '-'),
            ],
            [
              copy.runtime.fields.updated,
              formatTimestamp(dashboard.status?.state?.updated_at),
            ],
            [
              copy.runtime.fields.stopRequested,
              String(dashboard.status?.state?.stop_requested ?? false),
            ],
            [
              copy.runtime.fields.status,
              dashboard.status?.status_message ?? '-',
            ],
          ]}
        />
      </Panel>
      <Panel title={copy.runtime.panels.stageFlow} accent='cyan'>
        <TextList
          items={(dashboard.agentActivity?.stage_statuses || []).map(
            (stage: Record<string, string>) =>
              `${stage.stage} | ${stage.status} | ${stage.message}`,
          )}
        />
      </Panel>
      <Panel title={copy.runtime.panels.events} accent='amber'>
        <TextList items={runtimeEvents} />
      </Panel>
      <Panel title={copy.runtime.panels.supervisorTails} accent='rose'>
        <TextList items={supervisorTails} />
      </Panel>
    </div>
  );
}
