#!/usr/bin/env sh
set -eu

REPO_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
SIDECAR_DIR="${REPO_ROOT}/sidecars/research_flow"

if ! command -v uv >/dev/null 2>&1; then
	echo "uv is required for the research CrewAI Flow sidecar. Install uv before running it." >&2
	exit 1
fi

cd "${SIDECAR_DIR}"

if [ ! -d ".venv" ]; then
	echo "CrewAI Flow sidecar environment is not installed. Run 'pnpm run setup:research-flow' first." >&2
	exit 2
fi

UV_ENV_FILE_ARGS=""
if [ -f ".env" ]; then
	UV_ENV_FILE_ARGS="--env-file .env"
fi

HAS_DOTENV_OPENAI_KEY=0
if [ -f ".env" ] && grep -Eq '^OPENAI_API_KEY=.+$' ".env"; then
	HAS_DOTENV_OPENAI_KEY=1
fi

if [ -z "${OPENAI_API_KEY:-}" ] && [ "${HAS_DOTENV_OPENAI_KEY}" != "1" ] && [ "${AGENTIC_TRADER_ALLOW_CREWAI_NOOP:-0}" != "1" ]; then
	echo "CrewAI Flow sidecar run is intentionally gated until OPENAI_API_KEY is set." >&2
	echo "For the no-LLM placeholder smoke, run: AGENTIC_TRADER_ALLOW_CREWAI_NOOP=1 pnpm run run:research-flow" >&2
	exit 2
fi

# shellcheck disable=SC2086
uv run --locked --no-sync ${UV_ENV_FILE_ARGS} research-flow
