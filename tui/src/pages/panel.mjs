import { Box, Text } from 'ink';
import React from 'react';

const e = React.createElement;

/**
 * Render a bordered panel with a bold colored title and a list of text lines.
 *
 * @param {string} title - The panel title shown in bold at the top.
 * @param {Array<any>} lines - Lines to display inside the panel; each item will be converted to a string.
 * @param {string} [borderColor='cyan'] - Color used for the panel border and title text.
 * @returns {import('react').ReactElement} The Ink Box element containing the titled panel and its lines.
 */
function panel(title, lines, borderColor = 'cyan') {
  return e(
    Box,
    {
      flexDirection: 'column',
      borderStyle: 'round',
      borderColor,
      paddingX: 1,
      paddingY: 0,
      width: '100%',
    },
    e(Text, { color: borderColor, bold: true }, title),
    ...lines.map((line, index) =>
      e(Text, { key: `${title}-${index}`, wrap: 'truncate-end' }, String(line)),
    ),
  );
}

export { panel };
