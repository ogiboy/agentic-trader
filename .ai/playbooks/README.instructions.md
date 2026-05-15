# Playbooks

Playbooks are repo-native command recipes derived from useful advisory command
patterns. They are not executable wrappers and they do not depend on generated
tool directories.

Use them when a task needs a repeatable sequence:

- `pr-enhance.instructions.md`
- `code-review.instructions.md`
- `setup-validation.instructions.md`
- `security-scan.instructions.md`
- `browser-qa.instructions.md`
- `memory-retrieval.instructions.md`
- `ruflo-advisory-checks.instructions.md`
- `news-intelligence.instructions.md`
- `strategy-research-and-sweeps.instructions.md`
- `finance-evidence-reconciliation.instructions.md`

If a referenced playbook is missing, renamed, or incomplete, report the exact
path, choose the closest remaining workflow only when its scope is clear, and
mark the gap as documentation debt. Do not invent a replacement command
sequence from memory.

Each playbook should name:

1. when to use it
2. exact checks to run
3. what evidence to keep
4. what must not be automated

For V1 trading-intelligence work, prefer these pairings:

- News, macro, filing, Firecrawl, or Camofox work: `news-intelligence.instructions.md`
- Scanner presets, strategy families, backtests, sweeps, or proposal enrichment:
  `strategy-research-and-sweeps.instructions.md`
- Broker/accounting/reporting truth: `finance-evidence-reconciliation.instructions.md`

When two playbooks disagree, keep the stricter safety, evidence, and
operator-truth rule. Runtime gates, broker safety, and source attribution take
priority over convenience or shorter validation.
