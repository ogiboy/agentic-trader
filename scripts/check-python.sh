#!/usr/bin/env sh
set -eu

RUN_FLAGS="--locked --all-extras --group dev"
PYRIGHT_TARGETS="agentic_trader tests scripts"

if ! command -v uv >/dev/null 2>&1; then
	echo "uv is required for Agentic Trader Python checks. Run 'pnpm run install:python' after installing uv." >&2
	exit 1
fi

uv lock --check
uv run ${RUN_FLAGS} ruff check .
# shellcheck disable=SC2086
uv run ${RUN_FLAGS} pyright ${PYRIGHT_TARGETS}
uv run ${RUN_FLAGS} python -m pytest -q
