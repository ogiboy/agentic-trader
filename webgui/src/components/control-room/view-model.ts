import {
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
  return [
    [copy.currentCycle.runtime, dashboard?.status?.runtime_state ?? '-'],
    [
      copy.currentCycle.mode,
      dashboard?.status?.runtime_mode ?? dashboard?.doctor?.runtime_mode ?? '-',
    ],
    [
      copy.currentCycle.currentSymbol,
      dashboard?.status?.state?.current_symbol ?? '-',
    ],
    [
      copy.currentCycle.cycleCount,
      String(dashboard?.status?.state?.cycle_count ?? '-'),
    ],
    [
      copy.currentCycle.status,
      localizedStatusText(dashboard?.status?.status_message, copy),
    ],
    [
      copy.currentCycle.currentStage,
      dashboard?.agentActivity?.current_stage ?? '-',
    ],
    [
      copy.currentCycle.stageStatus,
      dashboard?.agentActivity?.current_stage_status ?? '-',
    ],
    [
      copy.currentCycle.lastOutcome,
      dashboard?.agentActivity?.last_outcome_message ??
        copy.currentCycle.waitingOutcome,
    ],
  ];
}

export function systemStatusViewItems(
  dashboard: DashboardData | null,
  copy: ControlRoomCopy,
): KeyValueItems {
  return systemStatusItems(dashboard, copy);
}
