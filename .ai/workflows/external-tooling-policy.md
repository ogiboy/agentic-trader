# External Tooling Policy

RuFlo, Context7, CodeRabbit, Sonar, GitHub helpers, browser automation, and
similar tools are system-level development aids. They may improve investigation,
review, documentation lookup, diff-risk scoring, or browser QA, but they are not
part of the Agentic Trader runtime unless a separate repo-owned `tools/` adapter
or runtime contract explicitly adopts a narrow capability.

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
- Do not treat a globally installed helper as product behavior until
  setup-status and the relevant runtime adapter can report its readiness,
  fallback behavior, and secret boundary.

## Runtime Tool Roots

`tools/` is allowed to hold optional helper infrastructure that the product may
inspect or start explicitly, such as Camofox browser infrastructure and future
Ollama/Firecrawl tool roots.
These helpers must stay opt-in, loopback-bound where they expose local services,
and outside broker/policy mutation. Prefer this resolution order:

1. repo-owned tool root with an explicit wrapper or adapter
2. user-configured host-system command or endpoint
3. safe built-in Python/JS fallback when one exists
4. degraded readiness with a clear operator message

`sidecars/` remains for isolated runtime packages with their own environment and
contract, such as CrewAI Flow. Do not move sidecars into `tools/` just because
they are optional.

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
