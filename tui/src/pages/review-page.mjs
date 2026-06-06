import { Box } from 'ink';
import React from 'react';
import {
  getMarketContextLines,
  getReplayLines,
  getReviewLines,
  getTraceLines,
  getTradeContextLines,
  renderUnavailableMessage,
} from '../line-formatters.mjs';
import { getCanonicalAnalysisLines } from '../review-lines.mjs';
import { panel } from './panel.mjs';

const e = React.createElement;

/**
 * Render the Review page with panels for run review, agent trace, memory-aware replay, trade context, and market context.
 *
 * @param {{ data: { review: Object, trace: Object, replay: Object, tradeContext: Object, marketContext: Object, canonicalAnalysis: Object } }} props
 * @param {Object} props.data - Dashboard snapshot subsets used to populate panels.
 *   Expected keys:
 *     - review: { available?: boolean, record?: Object, error?: string }
 *     - trace: { available?: boolean, record?: Object, error?: string }
 *     - replay: { available?: boolean, replay?: Object, error?: string }
 *     - tradeContext: Object
 *     - marketContext: Object
 *     - canonicalAnalysis: Object
 * @returns {import('react').ReactElement} An Ink layout containing review, trace, replay, trade-context, and market-context panels.
 */
function ReviewPage({ data }) {
  const review = data.review;
  const trace = data.trace;
  const replay = data.replay;
  const tradeContext = data.tradeContext;
  const marketContext = data.marketContext;
  const canonicalAnalysis = data.canonicalAnalysis;
  const reviewRecord = review.record;
  const traceRecord = trace.record;
  const replayState = replay.replay;

  const reviewLines =
    review.available === false
      ? renderUnavailableMessage(review.error)
      : getReviewLines(reviewRecord);

  const traceLines =
    trace.available === false
      ? renderUnavailableMessage(trace.error)
      : getTraceLines(traceRecord);

  const replayLines =
    replay.available === false
      ? renderUnavailableMessage(replay.error)
      : getReplayLines(replayState);

  const tradeContextLines = getTradeContextLines(tradeContext);
  const marketContextLines = getMarketContextLines(marketContext);
  const canonicalAnalysisLines = getCanonicalAnalysisLines(canonicalAnalysis);

  return e(
    Box,
    { flexDirection: 'column', width: '100%' },
    e(
      Box,
      { width: '100%' },
      e(
        Box,
        { width: '50%', paddingRight: 1 },
        panel('LATEST RUN REVIEW', reviewLines, 'green'),
      ),
      e(
        Box,
        { width: '50%', paddingLeft: 1 },
        panel('AGENT TRACE', traceLines.slice(0, 8), 'magenta'),
      ),
    ),
    e(
      Box,
      { width: '100%', marginTop: 1 },
      e(
        Box,
        { width: '100%' },
        panel('MEMORY-AWARE REPLAY', replayLines, 'yellow'),
      ),
    ),
    e(
      Box,
      { width: '100%', marginTop: 1 },
      e(
        Box,
        { width: '50%', paddingRight: 1 },
        panel('TRADE CONTEXT', tradeContextLines, 'cyan'),
      ),
      e(
        Box,
        { width: '50%', paddingLeft: 1 },
        panel('MARKET CONTEXT PACK', marketContextLines, 'blue'),
      ),
    ),
    e(
      Box,
      { width: '100%', marginTop: 1 },
      e(
        Box,
        { width: '100%' },
        panel('CANONICAL ANALYSIS', canonicalAnalysisLines, 'blue'),
      ),
    ),
  );
}

export { ReviewPage };
