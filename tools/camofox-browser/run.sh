#!/bin/bash
set -euo pipefail
# Local development script for camofox-browser
# Usage: ./run.sh [-p port]
# Example: ./run.sh -p 3001

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
CAMOFOX_PNPM="$ROOT_DIR/scripts/run-camofox-pnpm.sh"

CAMOFOX_PORT=3000
while getopts "p:" opt; do
  case $opt in
    p) CAMOFOX_PORT="$OPTARG" ;;
    *) echo "Usage: $0 [-p port]"; exit 1 ;;
  esac
done
export CAMOFOX_PORT

if [ ! -d "$SCRIPT_DIR/node_modules" ]; then
    echo "Camofox dependencies are missing." >&2
    echo "Run: pnpm run setup:camofox" >&2
    exit 1
fi

CAMOUFOX_CACHE_DIR="$("$CAMOFOX_PNPM" --ignore-workspace exec camoufox-js path 2>/dev/null || true)"
if [ -z "$CAMOUFOX_CACHE_DIR" ] || [ ! -e "$CAMOUFOX_CACHE_DIR" ]; then
    echo "Camoufox browser helper is not ready." >&2
    echo "Run explicitly after approval: make fetch-camofox" >&2
    exit 1
fi

echo "Starting camofox-browser on http://localhost:$CAMOFOX_PORT"
echo "Logs: /tmp/camofox-browser.log"
"$CAMOFOX_PNPM" --ignore-workspace run start 2>&1 | while IFS= read -r line; do
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $line"
done | tee -a /tmp/camofox-browser.log
