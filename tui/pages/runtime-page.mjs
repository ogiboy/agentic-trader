import { Box } from 'ink';
import React from 'react';
import { getSupervisorLogLines } from '../dashboard-defaults.mjs';
import {
  formatMarketSessionWithTradable,
  readinessLines,
} from '../line-formatters.mjs';
import { panel } from './panel.mjs';

const e = React.createElement;

/**
 * Render the Runtime page with runtime status, supervisor/stage flow, and recent events.
 *
 * @param {Object} data - Dashboard snapshot containing runtime and related information.
 *   Expected properties: `status`, `supervisor`, `broker`, `logs`, `agentActivity`,
 *   `review`, `calendar`, and `marketCache`.
 * @returns {import('react').ReactElement} The Ink component tree for the Runtime page.
 */
function RuntimePage({ data }) {
  const runtime = data.status;
  const supervisor = data.supervisor;
  const broker = data.broker;
  const events = data.logs;
  const agentActivity = data.agentActivity;
  const reviewRecord = data.review.record;
  const calendar = data.calendar;
  const marketCache = data.marketCache;
  const latestSnapshot = reviewRecord?.artifacts?.snapshot;
  const recentSummary =
    reviewRecord?.artifacts?.review?.summary ||
    'No persisted review summary yet.';

  return e(
    Box,
    { flexDirection: 'column', width: '100%' },
    e(
      Box,
      { width: '100%' },
      e(
        Box,
        { width: '50%', paddingRight: 1 },
        panel(
          'RUNTIME STATE',
          [
            `Runtime: ${runtime.runtime_state}`,
            `Mode: ${runtime.runtime_mode ?? runtime.state?.runtime_mode ?? data.doctor?.runtime_mode ?? '-'}`,
            `Live Process: ${runtime.live_process ? 'yes' : 'no'}`,
            `State: ${runtime.state?.state ?? '-'}`,
            `Symbols: ${(runtime.state?.symbols || []).join(', ') || '-'}`,
            `Interval: ${runtime.state?.interval ?? '-'}`,
            `Lookback: ${runtime.state?.lookback ?? '-'}`,
            `Max Cycles: ${runtime.state?.max_cycles ?? '-'}`,
            `Current Symbol: ${runtime.state?.current_symbol ?? '-'}`,
            `Cycle Count: ${runtime.state?.cycle_count ?? '-'}`,
            `PID: ${runtime.state?.pid ?? '-'}`,
            `Updated: ${runtime.state?.updated_at ?? '-'}`,
            `Heartbeat Age: ${runtime.age_seconds ?? '-'}s`,
            `Stop Requested: ${runtime.state?.stop_requested ?? false}`,
            `Background Mode: ${runtime.state?.background_mode ?? false}`,
            `Launch Count: ${runtime.state?.launch_count ?? 0}`,
            `Restart Count: ${runtime.state?.restart_count ?? 0}`,
            `Last Terminal State: ${runtime.state?.last_terminal_state ?? '-'}`,
            `Last Terminal At: ${runtime.state?.last_terminal_at ?? '-'}`,
            `Message: ${runtime.state?.message ?? '-'}`,
            `Current Stage: ${agentActivity?.current_stage ?? '-'}`,
            `Stage Status: ${agentActivity?.current_stage_status ?? '-'}`,
            `Stage Detail: ${agentActivity?.current_stage_message ?? '-'}`,
            `Last Completed Stage: ${agentActivity?.last_completed_stage ?? '-'}`,
            `Last Completed Detail: ${agentActivity?.last_completed_message ?? '-'}`,
            `Broker Backend: ${broker?.backend ?? '-'}`,
            `Broker State: ${broker?.state ?? '-'}`,
            `External Paper: ${broker?.external_paper ?? false}`,
            `Kill Switch: ${broker?.kill_switch_active ?? false}`,
            `V1 Paper Ready: ${data.v1Readiness?.paper_operations?.allowed ? 'yes' : 'no'}`,
            `Alpaca Paper Ready: ${data.v1Readiness?.alpaca_paper?.ready ? 'yes' : 'no'}`,
            `MTF Alignment: ${latestSnapshot?.mtf_alignment ?? '-'}`,
            `Higher Timeframe: ${latestSnapshot?.higher_timeframe ?? '-'}`,
            `Market Session: ${formatMarketSessionWithTradable(calendar.session)}`,
            `Snapshot Cache Mode: ${marketCache.mode}`,
            `Cached Snapshots: ${marketCache.count}`,
          ],
          'cyan',
        ),
      ),
      e(
        Box,
        { width: '50%', paddingLeft: 1 },
        panel(
          'SUPERVISOR / STAGE FLOW',
          [
            `Stdout Tail Lines: ${supervisor?.stdout_tail?.length ?? 0}`,
            `Stderr Tail Lines: ${supervisor?.stderr_tail?.length ?? 0}`,
            `Stdout Log: ${runtime.state?.stdout_log_path ?? '-'}`,
            `Stderr Log: ${runtime.state?.stderr_log_path ?? '-'}`,
            '',
            ...(agentActivity?.stage_statuses?.length
              ? agentActivity.stage_statuses.map(
                  (stage) =>
                    `${stage.stage}: ${stage.status} | ${stage.message}`,
                )
              : ['No stage flow recorded yet.']),
            '',
            `Latest Review Available: ${data.review.available !== false && reviewRecord ? 'yes' : 'no'}`,
            `Latest Review Summary: ${recentSummary}`,
            '',
            ...readinessLines(data),
            '',
            ...getSupervisorLogLines(supervisor),
          ],
          'green',
        ),
      ),
    ),
    e(
      Box,
      { width: '100%', marginTop: 1 },
      e(
        Box,
        { width: '100%' },
        panel(
          'RUNTIME EVENTS',
          events.length
            ? events.map(
                (event) =>
                  `${event.created_at} | ${event.level} | ${event.event_type} | ${event.symbol ?? '-'} | ${event.message}`,
              )
            : ['No runtime events recorded yet.'],
          'yellow',
        ),
      ),
    ),
  );
}

export { RuntimePage };
