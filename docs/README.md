# Agentic Trader Docs

This package is the operator-first documentation site for Agentic Trader. It is
a separate Next.js/Fumadocs app that explains the current runtime, setup,
operator surfaces, QA flow, and contributor boundaries without importing Python
runtime code.

## Commands

Run from the repository root unless you are intentionally working inside this
package:

```bash
pnpm dev:docs
pnpm --filter docs run lint
pnpm --filter docs run typecheck
pnpm --filter docs run build
```

For GitHub Pages parity:

```bash
pnpm run build:docs:pages
```

## Content Ownership

- `content/docs/en/` and `content/docs/tr/` hold the localized MDX pages.
- `lib/i18n/`, `lib/home/`, and `components/home/` own landing-page and locale
  content.
- `source.config.ts` and `lib/source.ts` own the Fumadocs content pipeline.
- App Router entrypoints live under `app/`.

Docs should describe shipped behavior, not desired future behavior. When a
runtime command, setup flow, control-room boundary, or safety rule changes, keep
the matching `.ai` notes and `ROADMAP.md` in sync.

## Styling And Formatting

This app shares the local-first Next.js/Tailwind/shadcn direction with
`webgui/`. Keep visual changes token-based and avoid adding build-time external
font fetches. Prettier is configured locally through `.prettierrc` and
`.prettierignore`; generated `next-env.d.ts` is intentionally ignored.
