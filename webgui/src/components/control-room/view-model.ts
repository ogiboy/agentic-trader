import
  {
    asRecord,
    asString,
    localizedStatusText,
    systemStatusItems,
    type DashboardData,
    type KeyValueItems,
  } from '../control-room.helpers';
import type {
  ControlRoomDiagnosticsCopySource,
} from './diagnostics-formatting';
import type { ControlRoomCurrentCycleCopy } from './intl-copy';

export function currentCycleItems(
  dashboard: DashboardData | null,
  copy: ControlRoomCurrentCycleCopy,
  diagnostics?: ControlRoomDiagnosticsCopySource,
): KeyValueItems {
  const status = asRecord(dashboard?.status);
  const state = asRecord(status.state);
  const doctor = asRecord(dashboard?.doctor);
  const agentActivity = asRecord(dashboard?.agentActivity);
  return [
    [copy.runtime, asString(status.runtime_state)],
    [
      copy.mode,
      asString(status.runtime_mode, asString(doctor.runtime_mode)),
    ],
    [
      copy.currentSymbol,
      asString(state.current_symbol),
    ],
    [
      copy.cycleCount,
      asString(state.cycle_count),
    ],
    [
      copy.status,
      localizedStatusText(status.status_message, diagnostics),
    ],
    [
      copy.currentStage,
      asString(agentActivity.current_stage),
    ],
    [
      copy.stageStatus,
      asString(agentActivity.current_stage_status),
    ],
    [
      copy.lastOutcome,
      asString(
        agentActivity.last_outcome_message,
        copy.waitingOutcome,
      ),
    ],
  ];
}

export function systemStatusViewItems(
  dashboard: DashboardData | null,
  diagnostics?: ControlRoomDiagnosticsCopySource,
): KeyValueItems {
  return systemStatusItems(dashboard, diagnostics);
}
