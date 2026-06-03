import { Box } from 'ink';
import React from 'react';
import {
  getInstructionResultLines,
  getRecentRunsLines,
  renderLinesFallback,
} from '../line-formatters.mjs';
import { panel } from './panel.mjs';

const e = React.createElement;

/**
 * Render the Settings page composed of Preferences, Recent Runs, Operator Instruction, and Composer panels.
 *
 * @param {Object} params - Component props.
 * @param {Object} params.data - Dashboard snapshot containing preferences and recentRuns used to populate panels.
 * @param {string} params.draft - Current instruction draft text shown in the composer.
 * @param {boolean} params.instructionBusy - Whether an instruction submit is in progress; displays a working indicator when true.
 * @param {'preview'|'apply'} params.instructionMode - Current instruction mode; shown in the composer header.
 * @param {Object|null} params.instructionResult - Result object from the last instruction invocation used to render the Operator Instruction panel.
 * @param {boolean} [params.compact=false] - When true, render condensed preference/recent-run summaries for tighter layouts.
 * @returns {React.Element} The Settings page React element tree.
 */
function SettingsPage({
  data,
  draft,
  instructionBusy,
  instructionMode,
  instructionResult,
  compact = false,
}) {
  const preferences = data.preferences;
  const recentRuns = data.recentRuns;
  const rawPreferenceLines = renderLinesFallback(
    'PREFERENCES',
    preferences.available,
    preferences.error,
    'Preferences are temporarily unavailable.',
  ) || [
    `Regions: ${(preferences.regions || []).join(', ') || '-'}`,
    `Exchanges: ${(preferences.exchanges || []).join(', ') || '-'}`,
    `Currencies: ${(preferences.currencies || []).join(', ') || '-'}`,
    `Sectors: ${(preferences.sectors || []).join(', ') || '-'}`,
    `Risk: ${preferences.risk_profile}`,
    `Style: ${preferences.trade_style}`,
    `Behavior: ${preferences.behavior_preset}`,
    `Agent Profile: ${preferences.agent_profile}`,
    `Agent Tone: ${preferences.agent_tone}`,
    `Strictness: ${preferences.strictness_preset}`,
    `Intervention: ${preferences.intervention_style}`,
    `Notes: ${preferences.notes || '-'}`,
  ];
  const preferenceLines =
    compact && preferences.available !== false
      ? [
          `Regions / Exchanges: ${(preferences.regions || []).join(', ') || '-'} / ${(preferences.exchanges || []).join(', ') || '-'}`,
          `Currencies / Sectors: ${(preferences.currencies || []).join(', ') || '-'} / ${(preferences.sectors || []).join(', ') || '-'}`,
          `Risk / Style: ${preferences.risk_profile} / ${preferences.trade_style}`,
          `Behavior / Strictness: ${preferences.behavior_preset} / ${preferences.strictness_preset}`,
          `Profile / Tone: ${preferences.agent_profile} / ${preferences.agent_tone}`,
          `Intervention: ${preferences.intervention_style}`,
          `Notes: ${preferences.notes || '-'}`,
        ]
      : rawPreferenceLines;
  const recentRunLines = getRecentRunsLines(recentRuns);
  const instructionLines = getInstructionResultLines(instructionResult);
  const composerLines = [
    `Mode: ${instructionMode}`,
    instructionBusy ? 'Working...' : 'Enter submit  |  [ ] switch mode',
    draft || '(type a safe operator instruction here)',
  ];

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
          'PREFERENCES',
          preferenceLines.slice(0, compact ? 7 : 12),
          'blue',
        ),
      ),
      e(
        Box,
        { width: '50%', paddingLeft: 1 },
        panel(
          'RECENT RUNS',
          recentRunLines.slice(0, compact ? 5 : 8),
          'yellow',
        ),
      ),
    ),
    e(
      Box,
      { width: '100%', marginTop: 1 },
      e(
        Box,
        { width: '100%' },
        panel('OPERATOR INSTRUCTION', instructionLines, 'green'),
      ),
    ),
    e(
      Box,
      { width: '100%', marginTop: 1 },
      e(Box, { width: '100%' }, panel('COMPOSER', composerLines, 'magenta')),
    ),
  );
}

export { SettingsPage };
