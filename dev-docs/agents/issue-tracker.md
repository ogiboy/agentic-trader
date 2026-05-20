# Issue Tracker: GitHub

Issues and PRDs for this repository live in GitHub Issues for `ogiboy/agentic-trader`.
Use the `gh` CLI from inside this checkout so the repository is inferred from
`git remote -v`.

## Conventions

- Create an issue: `gh issue create --title "..." --body "..."`
- Read an issue: `gh issue view <number> --comments`
- List issues: `gh issue list --state open --json number,title,body,labels,comments`
- Comment on an issue: `gh issue comment <number> --body "..."`
- Apply or remove labels: `gh issue edit <number> --add-label "..."`
- Close an issue: `gh issue close <number> --comment "..."`

Use heredocs or body files for multi-line issue bodies so shell quoting does not
corrupt reproduction steps, QA evidence, or acceptance criteria.

## Skill Contract

When a skill says "publish to the issue tracker", create a GitHub issue.

When a skill says "fetch the relevant ticket", run `gh issue view <number>
--comments` and include labels in the local analysis.

For V1 release work, prefer issues for real blockers that cannot be fixed in the
current slice, especially runtime readiness, broker/accounting evidence,
security posture, setup drift, changelog/release automation, and user-facing QA
gaps.
