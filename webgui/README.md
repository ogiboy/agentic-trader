# Agentic Trader Web GUI

This package is the local browser control room for Agentic Trader. It is a
Next.js App Router app that validates browser input and delegates to the Python
CLI/dashboard/runtime/chat/instruction/proposal contracts. It is not a second
trading runtime and must not bypass the paper-first, manual-approval gates.

## Commands

Run from the repository root unless you are intentionally working inside this
package:

```bash
pnpm dev:webgui
pnpm --filter webgui run lint
pnpm --filter webgui run typecheck
pnpm --filter webgui run build
```

The root dev command binds to `127.0.0.1:3210` and enables polling so local
browser QA matches the documented operator path.

## Control-Room Structure

`src/components/control-room.tsx` should stay a small state/render coordinator.
New work belongs in focused modules under `src/components/control-room/`:

- view files such as `overview-view.tsx`, `runtime-view.tsx`,
  `proposal-desk-view.tsx`, `review-view.tsx`, `memory-view.tsx`,
  `chat-view.tsx`, and `settings-view.tsx`
- shell and reusable UI primitives in `shell.tsx` and `primitives.tsx`
- state and view-model helpers in `state-hooks.ts`, `view-model.ts`, and
  `types.ts`
- action and request helpers in `actions.ts` and `action-request.ts`
- formatting helpers in `formatting.ts`, `diagnostics-formatting.ts`, and
  `context-formatting.ts`
- localized copy under `copy/`
- loading and unavailable states in `loading-panel.tsx`

Route handlers under `src/app/api/` should remain thin adapters over the Python
runtime contract. They should validate inputs, apply route guards, and return
clear errors without adding trading business logic.

## Styling And Formatting

The app uses the shared local-first Next.js/Tailwind/shadcn direction. Keep new
screen work token-based and scoped to components where possible. Prettier is
configured locally through `.prettierrc` and `.prettierignore`; generated
`next-env.d.ts` is intentionally ignored.
