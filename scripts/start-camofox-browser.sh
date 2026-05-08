#!/usr/bin/env sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
CAMOFOX_DIR="${AGENTIC_TRADER_RESEARCH_CAMOFOX_TOOL_DIR:-${AGENTIC_TRADER_CAMOFOX_TOOL_DIR:-$ROOT_DIR/tools/camofox-browser}}"

if [ ! -f "$CAMOFOX_DIR/package.json" ]; then
  printf '%s\n' "Camofox browser helper is missing at $CAMOFOX_DIR." >&2
  exit 1
fi

if [ -z "${CAMOFOX_ACCESS_KEY:-}" ] && [ -n "${CAMOFOX_API_KEY:-}" ]; then
  CAMOFOX_ACCESS_KEY="$CAMOFOX_API_KEY"
  export CAMOFOX_ACCESS_KEY
fi

if [ -z "${CAMOFOX_ACCESS_KEY:-}" ]; then
  printf '%s\n' "Refusing to start Camofox without CAMOFOX_ACCESS_KEY or CAMOFOX_API_KEY." >&2
  printf '%s\n' "Example: CAMOFOX_ACCESS_KEY=\$(openssl rand -hex 24) scripts/start-camofox-browser.sh" >&2
  exit 1
fi

export CAMOFOX_HOST="${CAMOFOX_HOST:-127.0.0.1}"
export CAMOFOX_PORT="${CAMOFOX_PORT:-9377}"
export CAMOFOX_BROWSER_PREWARM="${CAMOFOX_BROWSER_PREWARM:-false}"
export CAMOFOX_CRASH_REPORT_ENABLED="${CAMOFOX_CRASH_REPORT_ENABLED:-false}"

case "$CAMOFOX_HOST" in
  127.0.0.1|localhost|::1) ;;
  *)
    printf '%s\n' "Camofox host must remain loopback for Agentic Trader local research helpers." >&2
    exit 1
    ;;
esac

cd "$CAMOFOX_DIR"
exec npm start
