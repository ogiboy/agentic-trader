# QA Report 2026-04-11 Rerun

Branch: `qa-testing`
Environment: macOS, zsh, conda `trader` interpreter at `/opt/anaconda3/envs/trader/bin/python`
LLM status during rerun: Ollama reachable, `qwen3:8b` available

This report supersedes `.ai/qa/artifacts/qa-report-2026-04-11.md`, which was run while Ollama was unavailable.

## Summary

The strict LLM gate now passes, but the trading runtime cannot start because the existing DuckDB runtime database hits a migration parser error. Several previous UX findings remain valid. A new traceback was found in `supervisor-status`.

## Passed Checks

- `doctor` reports Ollama reachable and model available.
- `broker-status` reports paper default, live-disabled state, and kill-switch state clearly.
- `dashboard-snapshot` emits valid JSON.
- `observer-api` serves valid JSON for `/health`, `/dashboard`, and `/broker`.
- Ink one-shot render works when forced to use the conda Python module fallback.
- Review, trace, trade-context, and journal commands complete after the failed run command because they fall back to existing persisted records.

## Findings

### 1. Runtime cannot start against existing DuckDB because migration uses unsupported constrained `ALTER TABLE`

Severity: blocker
Surface: runtime launch / one-shot run / background run

Steps:

```bash
/opt/anaconda3/envs/trader/bin/python -m agentic_trader.cli run --symbol AAPL --interval 1d --lookback 180d
/opt/anaconda3/envs/trader/bin/python -m agentic_trader.cli launch --symbols AAPL --interval 1d --lookback 180d --continuous --background
```

Expected:

- With Ollama reachable and model available, runtime proceeds into the agent cycle.

Actual:

- Both paths block with:

```text
Parser Error: Adding columns with constraints not yet supported
```

Evidence:

- `.ai/qa/artifacts/strict-cycle-rerun.log`
- `.ai/qa/artifacts/background-runtime-rerun.log`

Recommendation:

- Update DuckDB migrations so `ALTER TABLE ADD COLUMN` never adds `NOT NULL`, `DEFAULT`, or other constraints in the same statement.
- Keep create-table schema strict for new DBs, but use unconstrained additive migrations for existing DBs.

### 2. `supervisor-status` crashes with `NameError: cast is not defined`

Severity: high
Surface: CLI daemon supervision

Steps:

```bash
/opt/anaconda3/envs/trader/bin/python -m agentic_trader.cli supervisor-status
```

Expected:

- Supervisor metadata and log tails render cleanly.

Actual:

- Command prints part of the supervisor table, then crashes:

```text
NameError: name 'cast' is not defined
```

Evidence:

- `.ai/qa/artifacts/background-runtime-rerun.log`

Recommendation:

- Import `cast` from `typing` or avoid `cast` in the render path.

### 3. Primary `agentic-trader` entrypoint resolves to an old global install

Severity: high
Surface: CLI entrypoint / Ink launch contract

Steps:

```bash
which agentic-trader
agentic-trader observer-api --help
```

Expected:

- `agentic-trader` resolves to the active project environment.
- Current commands such as `observer-api`, `broker-status`, and `supervisor-status` are available.

Actual:

- `which agentic-trader` returns `/Library/Frameworks/Python.framework/Versions/3.12/bin/agentic-trader`.
- That stale entrypoint does not include `observer-api`.
- The Ink JS launcher currently tries `AGENTIC_TRADER_CLI` before `AGENTIC_TRADER_PYTHON`, which can let a stale global entrypoint feed old JSON into the TUI.

Evidence:

- `.ai/qa/artifacts/entrypoint-mismatch-rerun.log`

Recommendation:

- Make Ink prefer `AGENTIC_TRADER_PYTHON` when present.
- Make the Python TUI launcher pass the active `sys.executable` as the primary contract.
- Keep documentation recommending `python -m pip install -e ".[dev]"` inside the active environment.

### 4. Ink and Rich status surfaces show a stale stage as currently running after runtime failure

Severity: high
Surface: Ink overview / Rich menu current cycle

Steps:

```bash
AGENTIC_TRADER_CLI=/tmp/missing-agentic-trader \
AGENTIC_TRADER_PYTHON=/opt/anaconda3/envs/trader/bin/python \
node tui/index.mjs --once
```

Expected:

- If runtime is inactive/failed, the current stage should not appear as actively running.

Actual:

- Runtime is shown as `inactive`, but current stage is shown as `risk` with status `running`.
- Last outcome is `service_failed`, so the UI mixes terminal failure with an in-progress stage.

Evidence:

- `.ai/qa/artifacts/ink-once-rerun.log`
- `.ai/qa/artifacts/rich-menu-smoke.log`

Recommendation:

- Update derived agent-activity logic to treat terminal service events as closing or interrupting any still-running stage.

### 5. Rich menu non-interactive EOF is reported as an action failure and exits with code 1

Severity: medium
Surface: Rich menu

Steps:

```bash
printf '2\n1\n\n7\n' | /opt/anaconda3/envs/trader/bin/python -m agentic_trader.cli menu
```

Expected:

- Input exhaustion should close cleanly or show a concise EOF/exit message.

Actual:

- Menu prints `Action Failed` with `EOF when reading a line`, then `Aborted.`
- Exit code is `1`.

Evidence:

- `.ai/qa/artifacts/rich-menu-smoke.log`

Recommendation:

- Catch `EOFError` around prompt loops and treat it like a clean operator exit.

### 6. Rich menu banner wraps into duplicated, hard-to-read ASCII at normal terminal width

Severity: low
Surface: Rich menu visual presentation

Evidence:

- `.ai/qa/artifacts/rich-menu-smoke.log`

Recommendation:

- Use a narrower banner for Rich menu or switch to compact branding when console width is below a safe threshold.

### 7. Doctor displays latest order as a raw tuple

Severity: medium
Surface: CLI/Rich doctor output

Steps:

```bash
/opt/anaconda3/envs/trader/bin/python -m agentic_trader.cli doctor
```

Expected:

- Latest order is formatted as readable fields or summarized as symbol/side/approved/order id.

Actual:

- Latest order is printed as a Python tuple.

Evidence:

- `.ai/qa/artifacts/environment-smoke-rerun.log`

Recommendation:

- Format latest order with the existing typed row semantics instead of `str(tuple)`.

## Not Fully Exercised

- Successful full cycle persistence because the runtime is blocked by the DuckDB migration issue.
- Background runtime live monitor after a successful agent cycle.
- Full interactive Ink hotkey navigation beyond one-shot render.
