#!/usr/bin/env sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT_DIR"

pnpm install
pnpm approve-builds --all

missing=0

require_dir() {
  if [ ! -d "$1" ]; then
    printf 'Missing expected Node workspace install directory: %s\n' "$1" >&2
    missing=1
  fi
}

require_dir "node_modules/.pnpm"
require_dir "webgui/node_modules"
require_dir "docs/node_modules"
require_dir "tui/node_modules"
require_dir "webgui/node_modules/next"
require_dir "docs/node_modules/next"
require_dir "tui/node_modules/ink"

if [ "$missing" -ne 0 ]; then
  printf '%s\n' "Node workspace install is incomplete. Run pnpm run setup:node from the repository root." >&2
  exit 1
fi

printf '%s\n' "Node workspace dependencies are installed for root, webgui, docs, and tui."
