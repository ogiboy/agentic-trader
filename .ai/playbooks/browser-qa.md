# Browser QA Playbook

Use this for WebGUI or docs visual behavior.

## WebGUI

1. Start the app through the repo script, not a stale global command:
   - `pnpm run dev:webgui`
2. Open `http://localhost:3210`.
3. Verify:
   - dashboard loads from current worktree CLI/runtime contracts
   - runtime controls show disabled/error states honestly
   - review, portfolio, risk, journal, and memory sections surface
     section-level unavailable states
   - no text overlap at desktop and mobile widths
   - no secret-like values in UI errors
4. Compare suspicious UI state against CLI JSON.
5. Optional advisory checks:
   - `ruflo route task "browser QA for WebGUI operator shell"`
   - `ruflo analyze diff --risk`

## Docs

1. Start docs or build static output:
   - `pnpm --filter docs build`
2. Verify English and Turkish routes.
3. Confirm operator-first pages distinguish product trading memory/review
   evidence from contributor `.ai` project notes.
4. Confirm screenshots or visual evidence only when it adds value.
5. Optional advisory checks:
   - `ruflo route task "docs QA for operator guide and localized routes"`
   - `ruflo analyze diff --risk`

## Browser Evidence Template

```text
App:
URL:
Viewport:
Scenario:
Expected:
Actual:
Runtime JSON cross-check:
Screenshot/artifact:
Risk:
```

## Do Not

- do not use browser UI state as the source of truth when CLI/runtime JSON
  disagrees
- do not fix visual polish by hiding unavailable/error states
