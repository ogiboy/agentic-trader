import { describe, expect, it } from 'vitest';

import {
  getCanonicalAnalysisLines,
  getFundamentalAssessmentLines,
} from './review-lines.mjs';

describe('TUI review evidence lines', () => {
  it('formats unavailable, missing, and populated canonical analysis snapshots', () => {
    expect(getCanonicalAnalysisLines({ available: false, error: 'locked' })).toEqual([
      'Unavailable in observer mode.',
      'locked',
    ]);
    expect(getCanonicalAnalysisLines(null)).toEqual([
      'No canonical analysis snapshot is available yet.',
    ]);

    const sourceAttributions = Array.from({ length: 10 }, (_value, index) => ({
      freshness: index % 2 === 0 ? 'fresh' : 'missing',
      provider_type: index % 2 === 0 ? 'market' : 'fundamental',
      source_name: `source-${index}`,
      source_role: index < 9 ? 'missing' : 'primary',
    }));
    const lines = getCanonicalAnalysisLines({
      snapshot: {
        completeness_score: 0.75,
        disclosures: [{ id: 'd1' }],
        fundamental: { attribution: { source_name: 'sec' } },
        macro: { attribution: { source_name: 'fred' } },
        market: { attribution: { source_name: 'alpaca' } },
        missing_sections: ['macro'],
        news_events: [{ title: 'news' }],
        source_attributions: sourceAttributions,
        summary: 'context ready',
      },
    });

    expect(lines).toContain('Summary: context ready');
    expect(lines).toContain(
      'Missing Sources: market:source-0, fundamental:source-1, market:source-2, fundamental:source-3, market:source-4, fundamental:source-5, market:source-6, fundamental:source-7 (+1 more)',
    );
    expect(lines).toContain('Sources Shown: 8/10 (+2 more)');
  });

  it('formats fundamental assessment evidence and fallbacks', () => {
    expect(getFundamentalAssessmentLines()).toEqual(['Fundamental Bias: -']);
    expect(
      getFundamentalAssessmentLines({
        evidence_vs_inference: {
          evidence: ['filing'],
          inference: ['margin expansion'],
          uncertainty: ['macro'],
        },
        overall_signal: 'constructive',
        risk_flags: ['valuation'],
      }),
    ).toEqual([
      'Fundamental Bias: constructive',
      'Fundamental Red Flags: valuation',
      'Fundamental Evidence: filing',
      'Fundamental Inference: margin expansion',
      'Fundamental Uncertainty: macro',
    ]);
  });
});
