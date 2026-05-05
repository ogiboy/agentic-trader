# Setup Validation Playbook

Use this after environment, package-manager, sidecar, or Codex workspace setup
changes.

## Root Checks

- `pnpm run setup`
- `pnpm run check`
- `pnpm run version:plan`
- `ruflo doctor -c version`
- `ruflo doctor -c node`
- `ruflo doctor -c npm`
- `ruflo hooks pre-command -- "pnpm run setup"`
- `ruflo hooks pre-command -- "pnpm run check"`

## Focused Checks

- Python only: `uv run python -m pytest -q -p no:cacheprovider <target>`
- Root lock: `uv lock --check`
- WebGUI: `pnpm --filter webgui lint && pnpm --filter webgui typecheck && pnpm --filter webgui build`
- Docs: `pnpm --filter docs lint && pnpm --filter docs typecheck && pnpm --filter docs build`
- TUI: `pnpm --filter tui check`
- Research Flow sidecar:
  - `pnpm run setup:research-flow`
  - `pnpm run check:research-flow`
  - `cd sidecars/research_flow && uv lock --check`

## Validate Semantics

- `setup` installs dependencies.
- `clean` removes generated artifacts only.
- `clean:deps` or `clean:all` removes installed dependencies.
- Root Python is uv-managed; Conda/Poetry are not the default path.
- Sidecar runtime does not implicitly install dependencies.

## Failure Triage

| Failure | First Check | Follow-Up |
| --- | --- | --- |
| root uv sync | `uv lock --check` | inspect `pyproject.toml` and `uv.lock` diff |
| workspace deps missing | `pnpm install --frozen-lockfile` | verify `pnpm-workspace.yaml` and package scripts |
| WebGUI build | `pnpm --filter webgui build` | run Browser QA if UI behavior changed |
| docs build | `pnpm --filter docs build` | verify static export assumptions |
| sidecar check | `pnpm run check:research-flow` | verify sidecar `.venv` and `uv.lock` |
| command runtime risk | `ruflo hooks pre-command -- "<command>"` | document residual risk before running |
