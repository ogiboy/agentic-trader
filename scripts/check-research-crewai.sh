#!/usr/bin/env sh
set -eu

REPO_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
SIDECAR_DIR="${REPO_ROOT}/sidecars/research-crewai"

if ! command -v uv >/dev/null 2>&1; then
	echo "uv is required for the research CrewAI sidecar. Install uv before running this check." >&2
	exit 1
fi

cd "${SIDECAR_DIR}"
uv sync --locked
uv run --locked python -m compileall -q src
uv run --locked research-crewai-check
uv run --locked python -c 'import sys; print(f"python={sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")'
