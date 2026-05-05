# Skill Usage Notes

These notes adapt useful global skill categories to Agentic Trader. They do not
make those tools project dependencies.

## Documentation Lookup

Use system-level documentation helpers for current API behavior, especially for
Next.js, CrewAI Flow, uv, GitHub Actions, and OpenAI/Codex behavior. Convert any
result into repo-native guidance before editing files.

## RuFlo / Flow-Compatible Advisory Commands

Use `.ai/skills/ruflo-codex.md` for the active command surface. The short rule:
MCP first, global `ruflo` second, `npx ruflo@latest` fallback third, and no
repo-local initialization unless explicitly requested.

## Browser Verification

Use browser automation for WebGUI and docs checks. Validate visual output against
runtime JSON contracts when state looks suspicious.

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

AgentDB, RuVector, ReasoningBank, and vector-search skills may inspire future
retrieval design, but the current repo contract remains local-first and
schema-backed. Do not add those dependencies without an explicit architecture
decision.
