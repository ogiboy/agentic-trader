function renderUnavailableMessage(error) {
  return [
    'Unavailable in observer mode.',
    error || 'The requested view could not read the runtime database.',
  ];
}

export function getFundamentalAssessmentLines(fundamental) {
  if (!fundamental) {
    return ['Fundamental Bias: -'];
  }
  const breakdown = fundamental.evidence_vs_inference || {};
  return [
    `Fundamental Bias: ${fundamental.overall_bias ?? fundamental.overall_signal ?? '-'}`,
    `Fundamental Red Flags: ${(fundamental.red_flags || fundamental.risk_flags || []).join(', ') || '-'}`,
    `Fundamental Evidence: ${(breakdown.evidence || []).join(' | ') || '-'}`,
    `Fundamental Inference: ${(breakdown.inference || []).join(' | ') || '-'}`,
    `Fundamental Uncertainty: ${(breakdown.uncertainty || []).join(' | ') || '-'}`,
  ];
}

export function getCanonicalAnalysisLines(canonicalAnalysis) {
  if (canonicalAnalysis?.available === false) {
    return renderUnavailableMessage(canonicalAnalysis.error);
  }
  const snapshot = canonicalAnalysis?.snapshot;
  if (!snapshot) {
    return ['No canonical analysis snapshot is available yet.'];
  }
  const sourceAttributions = snapshot.source_attributions || [];
  const formatSource = (source) =>
    `${source.provider_type}:${source.source_name} role=${source.source_role} freshness=${source.freshness}`;
  const sources = sourceAttributions.slice(0, 8).map(formatSource);
  const missingSourceItems = sourceAttributions.filter(
    (source) => source.source_role === 'missing',
  );
  const missingSources = missingSourceItems
    .slice(0, 8)
    .map((source) => `${source.provider_type}:${source.source_name}`)
    .join(', ');
  const hiddenSourceCount = Math.max(
    sourceAttributions.length - sources.length,
    0,
  );
  const hiddenSourceNote =
    hiddenSourceCount > 0 ? ` (+${hiddenSourceCount} more)` : '';
  const hiddenMissingCount = Math.max(missingSourceItems.length - 8, 0);
  const hiddenMissingNote =
    hiddenMissingCount > 0 ? ` (+${hiddenMissingCount} more)` : '';
  const sourceLines = sources.map((source) => `Source: ${source}`);
  return [
    `Summary: ${snapshot.summary || '-'}`,
    `Completeness: ${snapshot.completeness_score ?? '-'}`,
    `Missing: ${(snapshot.missing_sections || []).join(', ') || '-'}`,
    `Market Source: ${snapshot.market?.attribution?.source_name ?? '-'}`,
    `Fundamental Source: ${snapshot.fundamental?.attribution?.source_name ?? '-'}`,
    `Macro Source: ${snapshot.macro?.attribution?.source_name ?? '-'}`,
    `News Events: ${(snapshot.news_events || []).length}`,
    `Disclosures: ${(snapshot.disclosures || []).length}`,
    `Missing Sources: ${missingSources || '-'}${hiddenMissingNote}`,
    `Sources Shown: ${sources.length}/${sourceAttributions.length}${hiddenSourceNote}`,
    ...sourceLines,
  ];
}
