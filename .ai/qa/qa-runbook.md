# QA Runbook

## Goal

Validate Agentic Trader as a real operator would experience it across CLI, Ink TUI, Rich menu, daemon runtime, observer API, memory/review surfaces, and paper portfolio behavior.

This QA layer observes and reports. It does not fix code during the QA pass.

## Baseline Environment

Use the project environment unless the task says otherwise:

```bash
conda activate trader
python -m pip install -e ".[dev]"
```

If the shell cannot find the console entrypoint:

```bash
hash -r
which agentic-trader
python -m agentic_trader.cli doctor
```

Recommended core verification:

```bash
/opt/anaconda3/envs/trader/bin/python -m pytest -q -p no:cacheprovider
```

Recommended terminal smoke pass:

```bash
python scripts/qa/smoke_qa.py
```

Recommended terminal + code-quality pass:

```bash
python scripts/qa/smoke_qa.py --include-quality
```

Optional SonarQube pass:

```bash
SONAR_TOKEN=... python scripts/qa/smoke_qa.py --include-sonar
```

## Evidence Directory

Store manual QA evidence under:

```text
.ai/qa/artifacts/
```

Automated smoke QA writes each run into a timestamped subdirectory:

```text
.ai/qa/artifacts/smoke-YYYYMMDD-HHMMSS/
```

Suggested files:

- `run.log`
- `tui-pane.txt`
- `rich-menu-pane.txt`
- `observer-api.json`
- `session.cast`
- `screen-01.png`

Do not commit large binary evidence unless the task explicitly asks for it. Prefer text captures and concise reports.
Do not commit `.sonar/` output or Sonar tokens.

## Tooling

### pexpect

Use for repeatable CLI/Rich menu/Ink interaction.

Install only if missing:

```bash
python -m pip install pexpect
```

### tmux

Use for stable terminal sessions and pane capture:

```bash
tmux new-session -d -s agentic-trader-qa 'python main.py'
tmux capture-pane -t agentic-trader-qa -S - -p > .ai/qa/artifacts/tui-pane.txt
tmux kill-session -t agentic-trader-qa
```

### asciinema

Use when a complete terminal session recording is useful:

```bash
asciinema rec .ai/qa/artifacts/session.cast
```

### Screenshots

Use screenshots only for visual rendering issues that are hard to explain from text capture.

### Code Quality

Use `ruff`, `pytest`, IDE/Pylance or `pyright`, and SonarQube as complementary signals.

```bash
python -m ruff check .
python -m pytest -q -p no:cacheprovider
pyright
SONAR_TOKEN=... pysonar --sonar-host-url=http://localhost:9000 --sonar-project-key=agentic-trader-dev --sonar-token="$SONAR_TOKEN"
```

Never hardcode the Sonar token in tracked files. Prefer the `SONAR_TOKEN` environment variable.

## Standard QA Workflow

1. Read `AGENTS.md`, `.ai/current-state.md`, `.ai/tasks.md`, `.ai/debugging.md`, and the QA scenario being executed.
2. Start from a clean terminal.
3. Run the smallest relevant automated tests.
4. Exercise the target scenario manually.
5. Capture output, pane text, or API JSON.
6. Compare actual behavior against `.ai/qa/qa-checklist.md`.
7. Report issues with exact reproduction steps.
8. If no issues are found, record what was exercised and what evidence exists.

## Command Matrix

Core:

```bash
agentic-trader doctor
agentic-trader dashboard-snapshot
agentic-trader broker-status
agentic-trader supervisor-status
```

Primary UI:

```bash
agentic-trader
agentic-trader tui
python main.py
```

Admin / legacy UI:

```bash
agentic-trader menu
python main.py menu
```

Runtime:

```bash
agentic-trader launch --symbols AAPL,MSFT --interval 1d --lookback 180d --continuous --background
agentic-trader status
agentic-trader logs --limit 20
agentic-trader monitor --refresh-seconds 1
agentic-trader stop-service
agentic-trader restart-service
```

Review:

```bash
agentic-trader review-run
agentic-trader trace-run
agentic-trader trade-context
agentic-trader replay-run
```

Memory:

```bash
agentic-trader memory-explorer --symbol AAPL --interval 1d --lookback 180d --limit 5
agentic-trader retrieval-inspection
agentic-trader memory-policy
```

Portfolio:

```bash
agentic-trader portfolio
agentic-trader journal --limit 20
agentic-trader risk-report
```

Observer API:

```bash
agentic-trader observer-api --host 127.0.0.1 --port 8765
curl -s http://127.0.0.1:8765/health
curl -s http://127.0.0.1:8765/dashboard
curl -s http://127.0.0.1:8765/broker
```

## Failure Triage

When a scenario fails, classify the failing boundary:

- environment or entrypoint
- LLM/provider readiness
- market data or feature generation
- agent structured output contract
- manager/consensus/guard logic
- broker adapter or paper persistence
- runtime feed or daemon state
- DuckDB writer/observer behavior
- CLI/TUI/API presentation only

Start with the smallest failing boundary. Do not hide a product issue by only fixing presentation.

## QA Report Template

```text
Scenario:
Date:
Commit:
Environment:
Commands:
Expected:
Actual:
Evidence:
Severity:
Recommendation:
```
