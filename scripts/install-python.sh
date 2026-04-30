#!/usr/bin/env sh
set -eu

if [ -n "${CONDA_PREFIX:-}" ] && [ -x "${CONDA_PREFIX}/bin/python" ]; then
	PYTHON_BIN="${CONDA_PREFIX}/bin/python"
elif [ -x ".venv/bin/python" ]; then
	PYTHON_BIN="$(pwd)/.venv/bin/python"
else
	echo "Activate the 'trader' Conda env or create a local .venv before installing Python dependencies." >&2
	exit 1
fi

PYTHON_MINOR="$("${PYTHON_BIN}" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
case "${PYTHON_MINOR}" in
	3.12|3.13|3.14) ;;
	*)
		echo "Agentic Trader root runtime supports Python >=3.12,<3.15; got ${PYTHON_MINOR} at ${PYTHON_BIN}." >&2
		exit 1
		;;
esac

poetry env use "${PYTHON_BIN}" >/dev/null
poetry install --with dev --extras dev
