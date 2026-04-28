#!/usr/bin/env sh
set -eu

if [ -d ".venv" ]; then
	unset CONDA_DEFAULT_ENV CONDA_PREFIX CONDA_PREFIX_1 CONDA_PROMPT_MODIFIER CONDA_SHLVL || true
	export POETRY_VIRTUALENVS_IN_PROJECT=true
fi

PYRIGHT_TARGETS="agentic_trader tests scripts"
PYTHON_EXEC="$(poetry run python -c 'import sys; print(sys.executable)')"
CONDA_PYRIGHT=""

if [ -n "${CONDA_PREFIX:-}" ] && [ -x "${CONDA_PREFIX}/bin/pyright" ]; then
	CONDA_PYRIGHT="${CONDA_PREFIX}/bin/pyright"
else
	for candidate in \
		"${HOME}/anaconda3/bin/pyright" \
		"${HOME}/miniconda3/bin/pyright" \
		"/opt/anaconda3/bin/pyright" \
		"/opt/anaconda3/envs/trader/bin/pyright" \
		"/opt/miniconda3/bin/pyright"
	do
		if [ -x "${candidate}" ]; then
			CONDA_PYRIGHT="${candidate}"
			break
		fi
	done
fi

poetry check --lock
poetry run ruff check .

if poetry run sh -c 'command -v pyright >/dev/null 2>&1'; then
	# shellcheck disable=SC2086
	poetry run pyright ${PYRIGHT_TARGETS}
elif command -v pyright >/dev/null 2>&1; then
	# shellcheck disable=SC2086
	pyright --pythonpath "${PYTHON_EXEC}" ${PYRIGHT_TARGETS}
elif [ -n "${CONDA_PYRIGHT}" ]; then
	# shellcheck disable=SC2086
	"${CONDA_PYRIGHT}" --pythonpath "${PYTHON_EXEC}" ${PYRIGHT_TARGETS}
else
	echo "pyright is required. Run 'poetry install --with dev --extras dev' or install pyright on PATH." >&2
	exit 1
fi

poetry run python -m pytest -q
