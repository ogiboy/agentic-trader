#!/usr/bin/env sh
set -eu

if [ -n "${CONDA_PREFIX:-}" ] && [ -x "${CONDA_PREFIX}/bin/python" ]; then
	PYTHON_BIN="${CONDA_PREFIX}/bin/python"
elif [ -x ".venv/bin/python" ]; then
	PYTHON_BIN=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
	PYTHON_BIN="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
	PYTHON_BIN="$(command -v python)"
else
	echo "Python is required before installing Poetry dependencies." >&2
	exit 1
fi

if [ -n "${CONDA_PREFIX:-}" ] || [ -d ".venv" ]; then
	unset CONDA_DEFAULT_ENV CONDA_PREFIX CONDA_PREFIX_1 CONDA_PROMPT_MODIFIER CONDA_SHLVL || true
	export POETRY_VIRTUALENVS_IN_PROJECT=true
	poetry env use "${PYTHON_BIN}" >/dev/null
fi

poetry install --with dev --extras dev
