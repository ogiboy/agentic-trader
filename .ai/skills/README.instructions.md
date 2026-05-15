# Skill Usage Notes

These notes adapt useful global skill categories to Agentic Trader. They do not
make those tools project dependencies.

If a named external skill, MCP tool, CLI, or plugin is unavailable, continue
with local source review and tests. Record the missing tool only when it changes
the confidence of the result.

## Documentation Lookup

Use system-level documentation helpers for current API behavior, especially for
Next.js, CrewAI Flow, uv, GitHub Actions, and OpenAI/Codex behavior. Convert any
result into repo-native guidance before editing files.
If docs lookup fails, use installed package docs or source code before relying
on memory.

## RuFlo / Flow-Compatible Advisory Commands

Use `.ai/skills/ruflo-codex.instructions.md` for the active command surface.
Follow this order:

1. Use Codex-exposed RuFlo MCP tools.
2. Use the global `ruflo` binary.
3. Use `npx ruflo@latest` only when the global binary is unavailable.
4. Skip repo-local initialization unless the user explicitly requests it.
   If Ruflo MCP closes transport, stop the Ruflo sequence and use Codex-native
   review, tests, and explicit subagents instead.

## Browser Verification

Use browser automation for WebGUI and docs checks. Validate visual output against
runtime JSON contracts when state looks suspicious.

## Market News Research

Use `.ai/skills/market-news-research.instructions.md` for ticker, portfolio,
macro, filing, Firecrawl, Camofox, and sidecar evidence work. Normalize source
attribution, freshness, materiality, attempts, and redaction before evidence is
allowed to influence scanner, proposal, or review surfaces.

## Security Audit

Use security audit skills as advisory review lenses, then implement concrete
tests in this repo:

- origin/token/body validation
- observer loopback behavior
- fake secret redaction
- subprocess output caps/redaction
- sidecar/provider poisoning normalization

## GitHub And Release

Use GitHub/release skills for PR and CI inspection, but keep the repo's staged
branch policy authoritative:

- explicit PR base
- version bump before product-impacting branch push
- `CHANGELOG.md` release-flow owned
- `pnpm run version:plan`
- `pnpm run release:preview` for release/CI/package changes

## Memory And Retrieval

AgentDB, RuVector, ReasoningBank, and vector-search skills are advisory sources
for future retrieval design. The current repo contract remains local-first and
schema-backed. Do not add those dependencies without an explicit architecture
decision.
