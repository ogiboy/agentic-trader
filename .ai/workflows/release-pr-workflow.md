# Release And PR Workflow

Use this for branch publishing, PR creation, release automation, version fields,
binary workflows, changelog behavior, and package metadata.

## Pre-Push Checklist

1. `git status --short --branch`
2. Confirm target base branch explicitly. Do not default to `main` when the
   staged flow says `V1`, `webgui`, `devdocs`, or another base.
3. If product-impacting behavior changed, bump patch version consistently:
   - `pyproject.toml`
   - `agentic_trader/__init__.py`
   - root `package.json`
   - `webgui/package.json`
   - `docs/package.json`
   - `tui/package.json`
   - `sidecars/research_flow/pyproject.toml`
   - lockfile metadata touched by the version bump
4. Run `pnpm run version:plan`.
5. Run `pnpm run release:preview` for release, packaging, CI, binary, or package
   metadata changes, or document why it is not applicable.
6. Keep `CHANGELOG.md` release-flow owned unless the user explicitly asks to
   edit it.

## Advisory Commands

```bash
ruflo route task "release/pr: <short description>"
ruflo hooks pre-command -- "pnpm run version:plan"
ruflo hooks pre-command -- "pnpm run release:preview"
ruflo analyze diff --risk
```

Use GitHub CLI for real branch/PR state:

```bash
gh pr list --state open --head "$(git branch --show-current)" --json number,title,baseRefName,headRefName,url
gh pr view <number> --json number,title,baseRefName,headRefName,state,url
```

## PR Checklist

- Head branch name describes the work.
- Base branch is explicit in the PR body.
- PR title does not include assistant branding.
- Body lists changed surfaces, tests, version behavior, and release impact.
- If CI/release behavior changed, include the expected GitHub Actions path.
- If binaries are involved, distinguish workflow artifacts from GitHub Release
  publication.

## Stable Release Notes

- `pyproject.toml` is the canonical stable version source.
- Semantic-release owns stable changelog/tag stamping on `main`.
- Branch version previews are artifact identities, not stable app version
  changes unless tracked version files were intentionally bumped.
- Direct branch binary workflow runs may upload artifacts while skipping GitHub
  Release publication; release publication should happen from a tag/dispatch
  path.

## Go/No-Go

No-go when:

- version files disagree after a product-impacting branch push
- target PR base is ambiguous
- release preview fails for release/CI/package changes
- changelog ownership is unclear
- generated tool-state files are present in `git status`

## PR Checklist Template

```text
Branch:
Base:
Existing PR:
Version files:
Version plan:
Release preview:
Checks:
Risk:
PR action:
```
