import type { DashboardData } from '../control-room.helpers';
import
  {
    asRecord,
    asRecordArray,
    asString,
    formatTimestamp,
  } from '../control-room.helpers';
import type { ControlRoomCopy } from './labels';
import { KeyValueList, Panel, TextList } from './primitives';

export function RuntimeView({
  copy,
  dashboard,
}: Readonly<{ copy: ControlRoomCopy; dashboard: DashboardData }>) {
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
    : [copy.runtime.empty.events];
  const supervisorTails = [
    ...(stderrTail.length ? stderrTail : [copy.runtime.empty.stderr]),
    ...(stdoutTail.length ? stdoutTail : [copy.runtime.empty.stdout]),
  ];

  return (
    <div className='grid grid--2'>
      <Panel title={copy.runtime.panels.state} accent='lime'>
        <KeyValueList
          items={[
            [
              copy.runtime.fields.runtime,
              asString(status.runtime_state),
            ],
            [
              copy.runtime.fields.liveProcess,
              status.live_process ? copy.common.yes : copy.common.no,
            ],
            [
              copy.runtime.fields.pid,
              asString(state.pid),
            ],
            [
              copy.runtime.fields.currentSymbol,
              asString(state.current_symbol),
            ],
            [
              copy.runtime.fields.cycleCount,
              asString(state.cycle_count),
            ],
            [
              copy.runtime.fields.updated,
              formatTimestamp(state.updated_at),
            ],
            [
              copy.runtime.fields.stopRequested,
              asString(state.stop_requested, 'false'),
            ],
            [
              copy.runtime.fields.status,
              asString(status.status_message),
            ],
          ]}
        />
      </Panel>
      <Panel title={copy.runtime.panels.stageFlow} accent='cyan'>
        <TextList
          items={stageStatusRows.map(
            (stage) =>
              `${asString(stage.stage)} | ${asString(stage.status)} | ${asString(stage.message)}`,
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
