import { Box } from 'ink';
import React from 'react';
import {
  getAgentEventLines,
  getCurrentCycleLines,
  getStatusBorderColor,
  getSystemLines,
  providerLines,
  readinessLines,
} from '../line-formatters.mjs';
import { panel } from './panel.mjs';

const e = React.createElement;

/**
 * Render the Overview dashboard page showing runtime status, system information, and recent agent activity.
 * @param {object} props
 * @param {object} props.data - Dashboard snapshot used to populate panels; expected to include keys such as `doctor`, `status`, `preferences`, `calendar`, `broker`, `marketCache`, `marketContext`, `review`, and `agentActivity`.
 * @returns {import('react').ReactElement} The Ink/React element tree for the Overview page.
 */
function OverviewPage({ data, compact = false }) {
  const doctor = data.doctor;
  const runtime = data.status;
  const agentActivity = data.agentActivity;
  const agentEvents = agentActivity?.recent_stage_events || [];
  const currentCycleLines = getCurrentCycleLines(data, compact);
  const systemLines = getSystemLines(data, compact);

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
          'CURRENT CYCLE',
          currentCycleLines,
          getStatusBorderColor(runtime.runtime_state),
        ),
      ),
      e(
        Box,
        { width: '50%', paddingLeft: 1 },
        panel(
          'SYSTEM',
          systemLines,
          doctor.ollama_reachable && doctor.model_available ? 'green' : 'red',
        ),
      ),
    ),
    e(
      Box,
      { width: '100%', marginTop: 1 },
      e(
        Box,
        { width: '50%', paddingRight: 1 },
        panel('READINESS GATES', readinessLines(data), 'red'),
      ),
      e(
        Box,
        { width: '50%', paddingLeft: 1 },
        panel('PROVIDER WARNINGS', providerLines(data), 'yellow'),
      ),
    ),
    e(
      Box,
      { width: '100%', marginTop: 1 },
      e(
        Box,
        { width: '100%' },
        panel('AGENT ACTIVITY', getAgentEventLines(agentEvents), 'magenta'),
      ),
    ),
  );
}

export { OverviewPage };
