import { Box } from 'ink';
import React from 'react';
import {
  getExplorerLines,
  getInspectionLines,
  renderUnavailableMessage,
} from '../line-formatters.mjs';
import { panel } from './panel.mjs';

const e = React.createElement;

/**
 * Render the Memory page containing a "Similar Memories" panel and a "Retrieval Inspection" panel.
 *
 * @param {Object} data - Dashboard snapshot payload for this page.
 * @param {Object} data.memoryExplorer - Explorer results used to populate the "Similar Memories" panel; may include `available` and `error`.
 * @param {Object} data.retrievalInspection - Inspection results used to populate the "Retrieval Inspection" panel; may include `available` and `error`.
 * @returns {import('react').ReactElement} An Ink layout Box containing two side-by-side panels with memory matches and retrieval inspection lines.
 */
function MemoryPage({ data }) {
  const explorer = data.memoryExplorer;
  const inspection = data.retrievalInspection;

  const matchLines =
    explorer.available === false
      ? renderUnavailableMessage(explorer.error)
      : getExplorerLines(explorer);

  const retrievalLines =
    inspection.available === false
      ? renderUnavailableMessage(inspection.error)
      : getInspectionLines(inspection);

  return e(
    Box,
    { flexDirection: 'column', width: '100%' },
    e(
      Box,
      { width: '100%' },
      e(
        Box,
        { width: '50%', paddingRight: 1 },
        panel('SIMILAR PAST RUNS', matchLines.slice(0, 10), 'cyan'),
      ),
      e(
        Box,
        { width: '50%', paddingLeft: 1 },
        panel(
          'WHY THIS CONTEXT WAS USED',
          retrievalLines.slice(0, 12),
          'yellow',
        ),
      ),
    ),
  );
}

export { MemoryPage };
