#!/bin/bash
# Local development script for camofox-browser
# Usage: ./run.sh [-p port]
# Example: ./run.sh -p 3001

CAMOFOX_PORT=3000
while getopts "p:" opt; do
  case $opt in
    p) CAMOFOX_PORT="$OPTARG" ;;
    *) echo "Usage: $0 [-p port]"; exit 1 ;;
  esac
done
export CAMOFOX_PORT

if [ ! -d "node_modules" ]; then
    echo "Camofox dependencies are missing." >&2
    echo "Run: pnpm --dir tools/camofox-browser install --ignore-workspace --ignore-scripts" >&2
    exit 1
fi

CAMOUFOX_CACHE_DIR="$(pnpm --ignore-workspace exec camoufox-js path 2>/dev/null || true)"
if [ -z "$CAMOUFOX_CACHE_DIR" ] || [ ! -e "$CAMOUFOX_CACHE_DIR" ]; then
    echo "Camoufox browser helper is not ready." >&2
    echo "Run explicitly after approval: pnpm --dir tools/camofox-browser --ignore-workspace run fetch:browser" >&2
    exit 1
fi

echo "Starting camofox-browser on http://localhost:$CAMOFOX_PORT"
echo "Logs: /tmp/camofox-browser.log"
pnpm --ignore-workspace run start 2>&1 | while IFS= read -r line; do
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $line"
done | tee -a /tmp/camofox-browser.log
