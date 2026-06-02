#!/usr/bin/env sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage: scripts/launch-main.sh [options]

Bootstrap system tools, install project dependencies, then open the main
Agentic Trader launcher.

Options:
  --dry-run     Show the command sequence without mutating anything.
  --yes         Forward non-interactive yes to bootstrap ownership/setup prompts.
  -h, --help    Show this help.
EOF
}

BOOTSTRAP_ARGS=

while [ "$#" -gt 0 ]; do
  case "$1" in
    --)
      shift
      continue
      ;;
    --dry-run)
      DRY_RUN=1
      BOOTSTRAP_ARGS="$BOOTSTRAP_ARGS --dry-run"
      ;;
    --yes)
      BOOTSTRAP_ARGS="$BOOTSTRAP_ARGS --yes"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown option: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

run_or_print() {
  if [ "$DRY_RUN" -eq 1 ]; then
    printf '+ %s\n' "$*"
  else
    "$@"
  fi
}

cd "$ROOT_DIR"

# shellcheck disable=SC2086
scripts/bootstrap-system-tools.sh $BOOTSTRAP_ARGS
run_or_print pnpm run setup
run_or_print uv run --locked --all-extras --group dev python main.py
