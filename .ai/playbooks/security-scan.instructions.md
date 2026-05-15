# Security Scan Playbook

Use this before shipping security-sensitive, Web route, observer, sidecar,
provider, subprocess, release, or artifact changes.

If a security scanner, RuFlo security command, Codex Security tool, dependency
database, or local secret scan is unavailable, record the skipped source and run
the manual grep, source review, and negative tests that cover the same threat.
Do not mark a security-sensitive change clean on tool absence alone.

## Local Checks

- Advisory security route:
  - `ruflo route task "security review for current branch"`
  - `ruflo security secrets`
  - `ruflo security threats`
  - `ruflo analyze diff --risk`
- Search for hardcoded secrets:
  - `rg -n "(api[_-]?key|secret|token|password|private[_-]?key)\\s*[:=]" --glob '!node_modules' --glob '!runtime' --glob '!*.lock'`
- Check subprocess usage:
  - `rg -n "subprocess\\.|execFile|spawn\\(|exec\\(" agentic_trader webgui scripts tests`
- Check Web route boundaries:
  - `rg -n "origin|referer|content-length|rate|cooldown|token" webgui/src/app webgui/src/lib`
- Check observer binding:
  - `rg -n "observer|allow_nonlocal|is_loopback_host|ThreadingHTTPServer" agentic_trader tests scripts`

## Required Negative Tests

- fake secret redaction
- malformed JSON
- oversize body
- foreign origin
- disallowed runtime action
- blank/non-loopback observer host
- sidecar/provider non-JSON stderr redaction

## Evidence

Keep command output summaries, not raw secret-like payloads. If an advisory tool
reports a finding, verify it against source and add a focused test or an
explicit risk acceptance.

Generated scan reports, SARIF files, screenshots, runtime logs, and QA artifacts
must stay untracked unless the user explicitly asks to commit a sanitized
artifact. Redact fake and real secret-like values before sharing evidence.

## Security Report Template

```text
Surface:
Threat:
Exploit:
Impact:
Existing control:
Change/control:
Verification:
Residual risk:
```
