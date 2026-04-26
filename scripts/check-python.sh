#!/usr/bin/env sh
set -eu

if [ -d ".venv" ]; then
	unset CONDA_DEFAULT_ENV CONDA_PREFIX CONDA_PREFIX_1 CONDA_PROMPT_MODIFIER CONDA_SHLVL || true
	export POETRY_VIRTUALENVS_IN_PROJECT=true
fi

PYRIGHT_TARGETS="agentic_trader tests scripts"
PYTHON_EXEC="$(poetry run python -c 'import sys; print(sys.executable)')"

poetry check --lock
poetry run ruff check .

if poetry run sh -c 'command -v pyright >/dev/null 2>&1'; then
	poetry run pyright ${PYRIGHT_TARGETS}
elif command -v pyright >/dev/null 2>&1; then
	pyright --pythonpath "${PYTHON_EXEC}" ${PYRIGHT_TARGETS}
elif [ -x /opt/anaconda3/bin/pyright ]; then
	/opt/anaconda3/bin/pyright --pythonpath "${PYTHON_EXEC}" ${PYRIGHT_TARGETS}
else
	echo "pyright is required. Run 'poetry install --with dev --extras dev' or install pyright on PATH." >&2
	exit 1
fi

poetry run python -m pytest -q
