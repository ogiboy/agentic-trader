# Security Scan Playbook

Use this before shipping security-sensitive, Web route, observer, sidecar,
provider, subprocess, release, or artifact changes.

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
