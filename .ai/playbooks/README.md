# Playbooks

Playbooks are repo-native command recipes derived from useful advisory command
patterns. They are not executable wrappers and they do not depend on generated
tool directories.

Use them when a task needs a repeatable sequence:

- `pr-enhance.md`
- `code-review.md`
- `setup-validation.md`
- `security-scan.md`
- `browser-qa.md`
- `memory-retrieval.md`
- `ruflo-advisory-checks.md`

Each playbook should name:

1. when to use it
2. exact checks to run
3. what evidence to keep
4. what must not be automated
