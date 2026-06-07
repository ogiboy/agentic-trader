import { Box } from 'ink';
import React from 'react';
import {
  getInstructionResultLines,
  getRecentRunsLines,
  renderLinesFallback,
} from '../line-formatters.mjs';
import { tuiCopy } from '../copy.mjs';
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
  copy = tuiCopy,
}) {
  const settingsCopy = copy.settingsPage;
  const preferences = data.preferences;
  const recentRuns = data.recentRuns;
  const rawPreferenceLines = renderLinesFallback(
    settingsCopy.preferences,
    preferences.available,
    preferences.error,
    settingsCopy.preferencesUnavailable,
  ) || [
    `${settingsCopy.regions}: ${(preferences.regions || []).join(', ') || '-'}`,
    `${settingsCopy.exchanges}: ${(preferences.exchanges || []).join(', ') || '-'}`,
    `${settingsCopy.currencies}: ${(preferences.currencies || []).join(', ') || '-'}`,
    `${settingsCopy.sectors}: ${(preferences.sectors || []).join(', ') || '-'}`,
    `${settingsCopy.risk}: ${preferences.risk_profile}`,
    `${settingsCopy.style}: ${preferences.trade_style}`,
    `${settingsCopy.behavior}: ${preferences.behavior_preset}`,
    `${settingsCopy.agentProfile}: ${preferences.agent_profile}`,
    `${settingsCopy.agentTone}: ${preferences.agent_tone}`,
    `${settingsCopy.strictness}: ${preferences.strictness_preset}`,
    `${settingsCopy.intervention}: ${preferences.intervention_style}`,
    `${settingsCopy.notes}: ${preferences.notes || '-'}`,
  ];
  const preferenceLines =
    compact && preferences.available !== false
      ? [
          `${settingsCopy.regionsExchanges}: ${(preferences.regions || []).join(', ') || '-'} / ${(preferences.exchanges || []).join(', ') || '-'}`,
          `${settingsCopy.currenciesSectors}: ${(preferences.currencies || []).join(', ') || '-'} / ${(preferences.sectors || []).join(', ') || '-'}`,
          `${settingsCopy.riskStyle}: ${preferences.risk_profile} / ${preferences.trade_style}`,
          `${settingsCopy.behaviorStrictness}: ${preferences.behavior_preset} / ${preferences.strictness_preset}`,
          `${settingsCopy.profileTone}: ${preferences.agent_profile} / ${preferences.agent_tone}`,
          `${settingsCopy.intervention}: ${preferences.intervention_style}`,
          `${settingsCopy.notes}: ${preferences.notes || '-'}`,
        ]
      : rawPreferenceLines;
  const recentRunLines = getRecentRunsLines(recentRuns);
  const instructionLines = getInstructionResultLines(instructionResult);
  const composerLines = [
    `${settingsCopy.mode}: ${instructionMode}`,
    instructionBusy ? settingsCopy.working : settingsCopy.enterSubmit,
    draft || settingsCopy.typeInstruction,
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
          settingsCopy.preferences,
          preferenceLines.slice(0, compact ? 7 : 12),
          'blue',
        ),
      ),
      e(
        Box,
        { width: '50%', paddingLeft: 1 },
        panel(
          settingsCopy.recentRuns,
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
        panel(settingsCopy.operatorInstruction, instructionLines, 'green'),
      ),
    ),
    e(
      Box,
      { width: '100%', marginTop: 1 },
      e(
        Box,
        { width: '100%' },
        panel(settingsCopy.composer, composerLines, 'magenta'),
      ),
    ),
  );
}

export { SettingsPage };
