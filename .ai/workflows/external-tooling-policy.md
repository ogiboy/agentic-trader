# External Tooling Policy

RuFlo, Context7, CodeRabbit, Sonar, GitHub helpers, browser automation, and
similar tools are system-level development aids. They may improve investigation,
review, documentation lookup, diff-risk scoring, or browser QA, but they are not
part of the Agentic Trader runtime.

## Allowed Uses

- Ask advisory tools for routing, diff-risk, file-risk, test-gap, security, or
  performance suggestions.
- Use system-level documentation helpers for current framework/API guidance.
- Use browser/computer tools for local WebGUI/docs verification.
- Use GitHub tooling for explicit branch, PR, CI, and release inspection.
- Use Sonar/CodeRabbit findings as review input that must be verified against
  the actual checkout before accepting or rejecting.

## Forbidden Uses

- Do not initialize repo-local advisory state unless the user explicitly asks.
- Do not track generated hooks, daemon state, memory stores, local MCP config,
  or assistant-specific project files.
- Do not add advisory packages as root runtime dependencies.
- Do not let advisory agents mutate broker, policy, runtime mode, provider
  secrets, or execution paths.
- Do not auto-dispatch write-capable agents without a bounded task, write scope,
  and validation plan.

## If A Tool Generates Files

1. Inventory the generated files.
2. Adopt only useful ideas into `.ai/agents/`, `.ai/workflows/`,
   `.ai/playbooks/`, `.ai/helpers/`, or `.ai/skills/`.
3. Rewrite adopted content so it stands alone in this repository.
4. Reject cloud-first, auto-commit, daemon, hidden-hook, and dependency-forcing
   content unless a separate repo decision explicitly accepts it.
5. Delete the generated artifacts after the `.ai` guidance is self-contained.

## Advisory Checks Before Publishing

Use an advisory diff-risk/file-risk pass when available for:

- security changes
- broker, execution, storage, or runtime-mode changes
- Web route handler or observer API changes
- release, CI, packaging, version, or dependency changes
- broad changes touching five or more meaningful files

Record the result as supporting evidence only. Tests, source contracts, and the
operator-visible runtime truth remain authoritative.
