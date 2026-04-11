# QA Smoke Script

## What It Does

`scripts/qa/smoke_qa.py` is a small development-time smoke harness for the current terminal operator surfaces.

It checks:

- `agentic-trader doctor`
- `agentic-trader dashboard-snapshot`
- read-only JSON status surfaces such as `status`, `broker-status`, `supervisor-status`, `logs`, `preferences`, `portfolio`, and `memory-policy`
- primary Ink entry through `agentic-trader`
- root launcher entry through `python main.py`
- legacy Rich/admin menu through `agentic-trader menu`

The script uses `subprocess` for non-interactive commands and `pexpect` for interactive terminal surfaces. Interactive checks let the UI render, capture visible output, then try to exit with `q`, Ctrl+C, and finally forced termination if needed.

## How To Run

From the repository root:

```bash
python scripts/qa/smoke_qa.py
```

Recommended project environment:

```bash
conda activate trader
python -m pip install -e ".[dev]"
python scripts/qa/smoke_qa.py
```

To include local code-quality checks:

```bash
python scripts/qa/smoke_qa.py --include-quality
```

That adds:

- `python -m ruff check .`
- `python -m pytest -q -p no:cacheprovider`
- `pyright` when available on `PATH`

When `--include-sonar` is used together with `--include-quality`, the pytest step also writes a coverage XML report into the run artifact directory and passes it to SonarQube.

To include SonarQube analysis through `pysonar`:

```bash
SONAR_TOKEN=... python scripts/qa/smoke_qa.py --include-quality --include-sonar
```

Optional Sonar settings:

```bash
SONAR_HOST_URL=http://localhost:9000 \
SONAR_PROJECT_KEY=agentic-trader-dev \
SONAR_TOKEN=... \
python scripts/qa/smoke_qa.py --include-sonar
```

The token is read from the environment and is redacted in command artifacts.

The script intentionally runs the installed `agentic-trader` entrypoint from `PATH` for console-entrypoint checks. If your shell resolves an old entrypoint, the smoke harness should fail and leave evidence showing the resolved path in the summary JSON.

## Artifacts

Artifacts are written under:

```text
.ai/qa/artifacts/smoke-YYYYMMDD-HHMMSS/
```

Current files include:

- `doctor.log`
- `dashboard_snapshot.log`
- `main_entrypoint_tui.log`
- `python_main_tui.log`
- `rich_menu.log`
- `smoke-summary.json`

When quality checks are enabled, the same run directory can also include:

- `ruff_check.log`
- `pytest.log`
- `coverage.xml`
- `pyright.log`
- `pysonar.log`

The JSON summary includes each check name, pass/fail status, details, artifact path, the repo root, the run artifact directory, the Python interpreter used, and the resolved `agentic-trader` path.

## What It Does Not Cover Yet

This first version is intentionally conservative. It does not yet:

- run a full strict agent cycle
- start, monitor, stop, or restart the background daemon
- validate observer API endpoints
- exercise every Ink hotkey or Rich submenu
- inspect paper portfolio consistency after a trade cycle
- record tmux panes, asciinema sessions, or screenshots automatically
- replace the manual scenarios in `.ai/qa/qa-scenarios.md`

Use it as a fast repeatable smoke check before deeper manual QA.
