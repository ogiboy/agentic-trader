import
  {
    asRecord,
    asString,
    localizedStatusText,
    systemStatusItems,
    type DashboardData,
    type KeyValueItems,
  } from '../control-room.helpers';
import type { ControlRoomCopy } from './labels';

export function currentCycleItems(
  dashboard: DashboardData | null,
  copy: ControlRoomCopy,
): KeyValueItems {
  const status = asRecord(dashboard?.status);
  const state = asRecord(status.state);
  const doctor = asRecord(dashboard?.doctor);
  const agentActivity = asRecord(dashboard?.agentActivity);
  return [
    [copy.currentCycle.runtime, asString(status.runtime_state)],
    [
      copy.currentCycle.mode,
      asString(status.runtime_mode, asString(doctor.runtime_mode)),
    ],
    [
      copy.currentCycle.currentSymbol,
      asString(state.current_symbol),
    ],
    [
      copy.currentCycle.cycleCount,
      asString(state.cycle_count),
    ],
    [
      copy.currentCycle.status,
      localizedStatusText(status.status_message, copy),
    ],
    [
      copy.currentCycle.currentStage,
      asString(agentActivity.current_stage),
    ],
    [
      copy.currentCycle.stageStatus,
      asString(agentActivity.current_stage_status),
    ],
    [
      copy.currentCycle.lastOutcome,
      asString(
        agentActivity.last_outcome_message,
        copy.currentCycle.waitingOutcome,
      ),
    ],
  ];
}

export function systemStatusViewItems(
  dashboard: DashboardData | null,
  copy: ControlRoomCopy,
): KeyValueItems {
  return systemStatusItems(dashboard, copy);
}
