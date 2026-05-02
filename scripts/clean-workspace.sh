#!/usr/bin/env sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT_DIR"

remove_artifacts() {
  rm -rf \
    .pytest_cache \
    .ruff_cache \
    .mypy_cache \
    .pyright \
    .coverage \
    coverage.xml \
    htmlcov \
    build \
    dist \
    docs/.next \
    docs/out \
    docs/.source \
    webgui/.next \
    webgui/out \
    tui/dist
  find . \
    \( \
      -path "./.git" \
      -o -path "./.venv" \
      -o -path "./node_modules" \
      -o -path "./docs/node_modules" \
      -o -path "./webgui/node_modules" \
      -o -path "./tui/node_modules" \
      -o -path "./sidecars/research_flow/.venv" \
    \) -prune \
    -o -name "__pycache__" -type d -exec rm -rf {} +
  find . -maxdepth 1 -name "*.egg-info" -type d -exec rm -rf {} +
}

remove_dependencies() {
  rm -rf \
    .venv \
    node_modules \
    docs/node_modules \
    webgui/node_modules \
    tui/node_modules \
    sidecars/research_flow/.venv
}

case "${1:-}" in
  "")
    remove_artifacts
    printf '%s\n' "Removed build, test, and cache artifacts. Dependencies were kept."
    ;;
  --deps)
    remove_dependencies
    printf '%s\n' "Removed installed dependency directories."
    ;;
  --all)
    remove_artifacts
    remove_dependencies
    printf '%s\n' "Removed build/test/cache artifacts and installed dependency directories."
    ;;
  *)
    printf 'Usage: %s [--deps|--all]\n' "$0" >&2
    exit 2
    ;;
esac
