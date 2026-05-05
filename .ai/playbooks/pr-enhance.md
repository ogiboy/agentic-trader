# PR Enhance Playbook

Use this before pushing or opening a PR for a non-trivial branch.

## Steps

1. Inspect branch and base:
   - `git status --short --branch`
   - `git branch --show-current`
   - `gh pr list --state open --head "$(git branch --show-current)" --json number,baseRefName,headRefName,title,url`
2. Verify version behavior:
   - run `pnpm run version:plan`
   - for product-impacting changes, confirm all tracked version files agree
3. Run focused checks for touched files.
4. Run broader checks when the change touches runtime, WebGUI, docs, sidecar,
   setup, security, release, or five or more files.
5. Run advisory checks when available:
   - `ruflo route task "pr enhance for current branch"`
   - `ruflo analyze diff --risk`
   - `ruflo hooks pre-command -- "pnpm run check"`
6. Summarize changed surfaces, validation, release impact, and residual risk.
7. Create or update the PR against the explicit requested base.

## PR Body Template

```markdown
## Summary
-

## Surfaces Changed
- Runtime:
- Operator UI:
- Docs:
- Tests:
- Release/version:

## Validation
- [ ] Focused tests:
- [ ] `pnpm run check`:
- [ ] `pnpm run qa`:
- [ ] `pnpm run version:plan`:
- [ ] RuFlo diff-risk:

## Release Impact
- Version files:
- Changelog:
- Binary/docs workflow:

## Residual Risk
-
```

## Do Not Automate

- no auto-merge
- no default-to-main PR base
- no changelog edits unless this is a release/changelog task
- no generated tool-state files in the branch
