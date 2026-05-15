# Security Workflow

Use this for threat modeling, hardening, route/observer changes, provider and
sidecar ingestion, subprocess handling, secrets, logs, CI/CD, and artifact
handling.

If a security tool is unavailable, continue with manual source review and
negative tests. Do not treat advisory-tool absence as a clean security result.

## Attack Surface Inventory

Always classify affected surfaces:

- CLI and Rich command handlers
- Ink TUI
- WebGUI route handlers
- observer API
- research sidecar and provider adapters
- subprocess boundaries
- DuckDB, JSONL, runtime, QA, and release artifacts
- env and secret management
- CI/CD, release, and dependency supply chain

## STRIDE Lens

| Category               | Repo-Specific Questions                                                                                     |
| ---------------------- | ----------------------------------------------------------------------------------------------------------- |
| Spoofing               | Can a caller pretend to be localhost, same-origin, a trusted provider, or an approved operator?             |
| Tampering              | Can input mutate runtime mode, broker policy, provider evidence, storage, or release metadata unexpectedly? |
| Repudiation            | Is there an audit trail for runtime actions, subprocess calls, broker outcomes, and release decisions?      |
| Information Disclosure | Can secrets, raw prompts, provider payloads, stderr, logs, or QA artifacts leak?                            |
| Denial of Service      | Can oversize JSON, restart floods, regexes, subprocesses, network calls, or long QA paths stall the app?    |
| Elevation of Privilege | Can a read-only surface become an execution path or bypass paper/live gates?                                |

## Required Checks

- Cross-origin and host validation.
- Body size, JSON shape, enum allowlist, and malformed payload rejection.
- Optional token/session guard where route impact is operational.
- Rate limit, cooldown, and single-flight behavior for expensive actions.
- Secret redaction for logs, subprocess errors, JSON responses, and artifacts.
- Provider/source trust tier, provenance, freshness, and raw-text normalization.
- Prompt/data-poisoning protections: raw web/social text must not become direct
  prompt instruction.
- Fallback behavior fails closed in operation mode and stays explicit in
  training/evaluation paths.
- Observer API stays loopback-first; empty bind hosts are non-loopback.

## Advisory Commands

```bash
ruflo route task "security: <short description>"
ruflo security secrets
ruflo security threats
ruflo security scan
ruflo security defend --help
ruflo analyze diff --risk
ruflo hooks pre-command -- "pnpm run check"
```

Use the security commands as triage, not as proof. Every accepted finding needs
a source reference and a test or risk acceptance.
If a command writes reports or scans dependencies, keep generated artifacts out
of git unless the task explicitly asks for a tracked report.

## Minimum Negative Tests

- Foreign origin request rejected.
- Malformed or oversize JSON rejected.
- Disallowed action rejected.
- Fake token/key in stderr or provider failure is masked.
- Non-loopback or blank observer host requires explicit override/token.
- Sidecar/provider poisoning sample is normalized or rejected before prompt use.

## Output Format

1. Threats found
2. Controls already present
3. Changes made
4. Negative tests run
5. Residual risk
6. Follow-up checklist

## STRIDE Finding Template

```text
Priority:
Surface:
STRIDE:
Exploit:
Impact:
Existing control:
Proposed control:
Verification:
Residual risk:
```
