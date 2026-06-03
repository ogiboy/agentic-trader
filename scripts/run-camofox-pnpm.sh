#!/usr/bin/env sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
CAMOFOX_DIR="${AGENTIC_TRADER_RESEARCH_CAMOFOX_TOOL_DIR:-${AGENTIC_TRADER_CAMOFOX_TOOL_DIR:-$ROOT_DIR/tools/camofox-browser}}"

if [ ! -f "$CAMOFOX_DIR/package.json" ]; then
  printf '%s\n' "Camofox browser helper is missing at $CAMOFOX_DIR." >&2
  exit 1
fi

cd "$CAMOFOX_DIR"
exec pnpm --pm-on-fail=ignore "$@"
