#!/usr/bin/env sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
YES=0
DRY_RUN=0
CORE_ONLY=0
INCLUDE_DEV_TOOLS=0
INCLUDE_BROWSER_TOOLS=0
SUMMARY_FILE="${TMPDIR:-/tmp}/agentic-trader-bootstrap-summary.$$"
CHOSEN_OWNERSHIP_MODE=
trap 'rm -f "$SUMMARY_FILE"' EXIT INT TERM

usage() {
  cat <<'EOF'
Usage: scripts/bootstrap-system-tools.sh [options]

Checks and optionally installs system-level tools used around Agentic Trader.
Installs are explicit and interactive unless --yes is passed.

Options:
  --yes                     Run accepted install steps without prompting.
  --dry-run                 Print intended actions without running installers.
  --core-only               Skip optional runtime/developer/browser tools.
  --include-dev-tools       Offer developer advisory tools such as RuFlo.
  --include-browser-tools   Legacy alias; Camofox setup is offered by default.
  -h, --help                Show this help.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --)
      shift
      break
      ;;
    --yes) YES=1 ;;
    --dry-run) DRY_RUN=1 ;;
    --core-only) CORE_ONLY=1 ;;
    --include-dev-tools) INCLUDE_DEV_TOOLS=1 ;;
    --include-browser-tools) INCLUDE_BROWSER_TOOLS=1 ;;
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

has_cmd() {
  command -v "$1" >/dev/null 2>&1
}

run_cmd() {
  if [ "$DRY_RUN" -eq 1 ]; then
    printf '+ %s\n' "$*"
  else
    "$@"
  fi
}

record_summary() {
  status=$1
  label=$2
  reason=${3:-}
  next_action=${4:-}
  printf '%s\t%s\t%s\t%s\n' "$status" "$label" "$reason" "$next_action" >> "$SUMMARY_FILE"
}

summary_icon() {
  case "$1" in
    done) printf '✓' ;;
    planned) printf '•' ;;
    deferred) printf '…' ;;
    not_done) printf '✗' ;;
    *) printf '-' ;;
  esac
}

render_summary() {
  printf '\n%s\n' "Bootstrap summary"
  if [ ! -s "$SUMMARY_FILE" ]; then
    printf '%s\n' "  No bootstrap actions were recorded."
    return 0
  fi
  while IFS='	' read -r status label reason next_action; do
    printf '  %s %-8s %s\n' "$(summary_icon "$status")" "$status" "$label"
    if [ -n "$reason" ]; then
      printf '             why:  %s\n' "$reason"
    fi
    if [ -n "$next_action" ]; then
      printf '             next: %s\n' "$next_action"
    fi
  done < "$SUMMARY_FILE"
}

ask_yes() {
  prompt=$1
  if [ "$YES" -eq 1 ]; then
    return 0
  fi
  if [ "$DRY_RUN" -eq 1 ]; then
    printf '? %s [dry-run assumes yes]\n' "$prompt"
    return 0
  fi
  printf '%s [y/N] ' "$prompt"
  read -r answer || answer=
  case "$answer" in
    y|Y|yes|YES) return 0 ;;
    *) return 1 ;;
  esac
}

require_homebrew() {
  if has_cmd brew; then
    return 0
  fi
  printf '%s\n' "Homebrew is not installed or not on PATH. Install it first for automatic macOS tool setup." >&2
  return 1
}

install_brew_tool() {
  command_name=$1
  formula=$2
  label=$3
  if has_cmd "$command_name"; then
    printf '✓ %s found at %s\n' "$label" "$(command -v "$command_name")"
    record_summary done "$label" "found at $(command -v "$command_name")"
    return 0
  fi
  printf '✗ %s not found\n' "$label"
  if ask_yes "Install $label with Homebrew ($formula)?"; then
    require_homebrew || return 1
    if run_cmd brew install "$formula"; then
      if [ "$DRY_RUN" -eq 1 ]; then
        record_summary planned "$label" "would install with Homebrew formula $formula"
      else
        record_summary done "$label" "installed with Homebrew formula $formula"
      fi
    else
      record_summary not_done "$label" "Homebrew install failed for formula $formula"
      return 1
    fi
  else
    record_summary deferred "$label" "not installed; user declined Homebrew install" "Install $formula manually or rerun make bootstrap."
  fi
}

install_npm_global() {
  command_name=$1
  package_name=$2
  label=$3
  if has_cmd "$command_name"; then
    printf '✓ %s found at %s\n' "$label" "$(command -v "$command_name")"
    record_summary done "$label" "found at $(command -v "$command_name")"
    return 0
  fi
  printf '✗ %s not found\n' "$label"
  if ! has_cmd npm; then
    printf '%s\n' "npm is required before installing $label." >&2
    record_summary deferred "$label" "npm is required before installing $package_name" "Install Node.js/npm, then rerun make bootstrap."
    return 0
  fi
  if ask_yes "Install $label globally with npm ($package_name)?"; then
    if run_cmd npm install -g "$package_name"; then
      if [ "$DRY_RUN" -eq 1 ]; then
        record_summary planned "$label" "would install npm package $package_name globally"
      else
        record_summary done "$label" "installed npm package $package_name globally"
      fi
    else
      record_summary not_done "$label" "npm global install failed for $package_name"
      return 1
    fi
  else
    record_summary deferred "$label" "not installed; user declined npm global install" "Install $package_name manually or rerun make bootstrap."
  fi
}

current_tool_ownership() {
  tool=$1
  if [ "$DRY_RUN" -eq 1 ] || ! has_cmd node; then
    printf '%s\n' undecided
    return 0
  fi
  node --input-type=module -e 'import { ownershipModeFor } from "./scripts/lib/app-lifecycle.mjs"; console.log(ownershipModeFor(process.argv[1]));' "$tool" 2>/dev/null || printf '%s\n' undecided
}

record_tool_ownership() {
  tool=$1
  mode=$2
  label=$3
  if [ "$DRY_RUN" -eq 1 ]; then
    printf '+ record %s ownership as %s\n' "$tool" "$mode"
    record_summary planned "$label ownership" "would record $mode in runtime/setup/tool-ownership.json"
    return 0
  fi
  if ! has_cmd node; then
    record_summary deferred "$label ownership" "Node.js is required to persist tool ownership"
    return 0
  fi
  if node --input-type=module -e 'import { persistToolOwnership } from "./scripts/lib/app-lifecycle.mjs"; persistToolOwnership({ [process.argv[1]]: process.argv[2] }, "bootstrap");' "$tool" "$mode"; then
    record_summary done "$label ownership" "recorded $mode in runtime/setup/tool-ownership.json"
  else
    record_summary not_done "$label ownership" "could not persist $mode"
    return 1
  fi
}

choose_tool_ownership() {
  tool=$1
  label=$2
  current_mode=$(current_tool_ownership "$tool")
  if [ "$current_mode" != "undecided" ]; then
    CHOSEN_OWNERSHIP_MODE=$current_mode
    printf '✓ %s ownership already recorded as %s\n' "$label" "$current_mode"
    record_summary done "$label ownership" "already recorded as $current_mode in runtime/setup/tool-ownership.json" "Change with agentic-trader tool-ownership set --${tool}-owner app-owned --json, or set AGENTIC_TRADER_RESELECT_OWNERSHIP=1 before make bootstrap."
    if [ "${AGENTIC_TRADER_RESELECT_OWNERSHIP:-0}" != "1" ]; then
      return 0
    fi
    if ask_yes "Change $label ownership to app-managed? Choose no to keep $current_mode."; then
      CHOSEN_OWNERSHIP_MODE=app-owned
      record_tool_ownership "$tool" app-owned "$label"
    fi
    return 0
  fi
  if ask_yes "Use app-managed $label for Agentic Trader lifecycle? Choose no to keep using host-managed $label."; then
    CHOSEN_OWNERSHIP_MODE=app-owned
    record_tool_ownership "$tool" app-owned "$label"
  else
    CHOSEN_OWNERSHIP_MODE=host-owned
    record_tool_ownership "$tool" host-owned "$label"
  fi
}

setup_agentic_trader_path() {
  entrypoint="$ROOT_DIR/.venv/bin/agentic-trader"
  target_dir="$HOME/.local/bin"
  target="$target_dir/agentic-trader"
  if has_cmd agentic-trader; then
    resolved_entrypoint=$(command -v agentic-trader)
    if [ -x "$entrypoint" ] && [ "$resolved_entrypoint" != "$entrypoint" ]; then
      printf '⚠ agentic-trader resolves at %s, not this worktree entrypoint %s\n' "$resolved_entrypoint" "$entrypoint"
      if ask_yes "Update $target to point at this worktree's agentic-trader entrypoint?"; then
        run_cmd mkdir -p "$target_dir"
        if [ "$DRY_RUN" -eq 1 ]; then
          printf '+ ln -sf %s %s\n' "$entrypoint" "$target"
      else
        ln -sf "$entrypoint" "$target"
      fi
      if [ "$DRY_RUN" -eq 1 ]; then
        record_summary planned "agentic-trader PATH entrypoint" "would update $target to this worktree"
      else
        record_summary done "agentic-trader PATH entrypoint" "updated $target to this worktree"
      fi
        printf '%s\n' "Ensure $target_dir appears before stale global installs in PATH."
      else
        record_summary deferred "agentic-trader PATH entrypoint" "still resolves to $resolved_entrypoint" "Run make setup, then rerun make bootstrap if this worktree should own the shell entrypoint."
      fi
      return 0
    fi
    printf '✓ agentic-trader already resolves at %s\n' "$resolved_entrypoint"
    record_summary done "agentic-trader PATH entrypoint" "resolves at $resolved_entrypoint"
    return 0
  fi
  if [ ! -x "$entrypoint" ]; then
    printf '%s\n' "agentic-trader entrypoint is not installed yet. Run make setup first, then rerun make bootstrap."
    record_summary deferred "agentic-trader PATH entrypoint" "local .venv entrypoint is not installed yet" "Run make setup, then rerun make bootstrap."
    return 0
  fi
  if ask_yes "Create/update $target so agentic-trader works from any shell?"; then
    run_cmd mkdir -p "$target_dir"
    if [ "$DRY_RUN" -eq 1 ]; then
      printf '+ ln -sf %s %s\n' "$entrypoint" "$target"
    else
      ln -sf "$entrypoint" "$target"
    fi
    if [ "$DRY_RUN" -eq 1 ]; then
      record_summary planned "agentic-trader PATH entrypoint" "would create or update $target"
    else
      record_summary done "agentic-trader PATH entrypoint" "created or updated $target"
    fi
    printf '%s\n' "Ensure $target_dir is in PATH."
  else
    record_summary deferred "agentic-trader PATH entrypoint" "user declined shell entrypoint update" "Run make setup and rerun make bootstrap when PATH should point at this checkout."
  fi
}

# setup_camofox_browser ensures the tools/camofox-browser helper exists, offers
# to install its local dependencies, and optionally downloads or updates the
# Camoufox browser binary. The helper uses the `camoufox-js` npm package as the
# Node.js bridge/fetch CLI for Camoufox; that package name is expected.
setup_camofox_browser() {
  camofox_dir="$ROOT_DIR/tools/camofox-browser"
  if [ ! -f "$camofox_dir/package.json" ]; then
    printf '%s\n' "Camofox browser helper is not present under tools/camofox-browser."
    record_summary deferred "Camofox browser helper" "tools/camofox-browser/package.json is missing" "Restore the helper package or skip Camofox until the source tree includes it."
    return 0
  fi
  choose_tool_ownership camofox "Camofox"
  if [ "$CHOSEN_OWNERSHIP_MODE" != "app-owned" ]; then
    record_summary deferred "Camofox browser helper" "Camofox ownership is $CHOSEN_OWNERSHIP_MODE; app-managed dependency install skipped" "Run agentic-trader tool-ownership set --camofox-owner app-owned --json, then rerun make bootstrap."
    return 0
  fi
  if ! has_cmd pnpm; then
    printf '%s\n' "pnpm is required for optional Camofox helper setup. Install pnpm first, then rerun make bootstrap ARGS=\"--include-browser-tools\"."
    record_summary deferred "Camofox browser helper" "pnpm is required for local dependency setup" "Install pnpm, then rerun make bootstrap."
    return 0
  fi
  if [ -d "$camofox_dir/node_modules" ]; then
    printf '✓ Camofox browser dependencies appear installed\n'
    record_summary done "Camofox dependencies" "node_modules already present"
  else
    printf '%s\n' "Camofox dependency install is local and skips browser downloads by default."
    printf '%s\n' "It installs the helper's Node dependencies, including camoufox-js: the Camoufox JS bridge/fetch CLI."
    if ask_yes "Install optional Camofox browser helper dependencies now?"; then
      if run_cmd scripts/run-camofox-pnpm.sh install --ignore-workspace --ignore-scripts; then
        if [ "$DRY_RUN" -eq 1 ]; then
          record_summary planned "Camofox dependencies" "would run local pnpm install without browser download"
        else
          record_summary done "Camofox dependencies" "installed local helper dependencies without browser download"
        fi
      else
        record_summary not_done "Camofox dependencies" "pnpm install failed"
        return 1
      fi
    else
      record_summary deferred "Camofox dependencies" "user skipped local helper dependency install" "Run make setup-camofox or rerun make bootstrap to install helper dependencies."
    fi
  fi
  printf '%s\n' "Camoufox browser binary download is separate and can be large."
  printf '%s\n' "The fetch command is provided by camoufox-js and downloads the Camoufox browser cache used by this helper."
  if ask_yes "Download/update the Camoufox browser binary now?"; then
    if run_cmd scripts/run-camofox-pnpm.sh --ignore-workspace run fetch:browser; then
      if [ "$DRY_RUN" -eq 1 ]; then
        record_summary planned "Camoufox browser binary" "would fetch optional browser binary"
      else
        record_summary done "Camoufox browser binary" "download/update completed"
      fi
    else
      record_summary not_done "Camoufox browser binary" "browser binary fetch failed"
      return 1
    fi
  else
    record_summary deferred "Camoufox browser binary" "large browser download was skipped" "Run make fetch-camofox or rerun make bootstrap when browser automation is needed."
  fi
}

printf '%s\n' "Agentic Trader system bootstrap"
printf '%s\n' "Workspace: $ROOT_DIR"

install_brew_tool uv uv "uv"
install_brew_tool node node "Node.js"
if has_cmd corepack && ! has_cmd pnpm; then
  if ask_yes "Enable Corepack before checking pnpm? This runs 'corepack enable' and may require elevated privileges."; then
    if ! run_cmd corepack enable; then
      printf '%s\n' "corepack enable failed. You may need sudo or a manual pnpm install; continuing to the Homebrew pnpm check."
      record_summary not_done "Corepack" "corepack enable failed"
    else
      record_summary done "Corepack" "corepack enable completed"
    fi
  fi
fi
install_brew_tool pnpm pnpm "pnpm"
setup_agentic_trader_path

if [ "$CORE_ONLY" -eq 0 ]; then
  install_brew_tool ollama ollama "Ollama"
  if has_cmd ollama; then
    choose_tool_ownership ollama "Ollama"
    printf '%s\n' "Use agentic-trader model-service status/start/pull to inspect or run app-managed Ollama."
  else
    record_summary deferred "Ollama ownership" "Ollama is not available yet"
  fi
  install_npm_global firecrawl firecrawl-cli "Firecrawl CLI"
  if has_cmd firecrawl; then
    choose_tool_ownership firecrawl "Firecrawl"
    printf '%s\n' "Firecrawl needs auth before use: run firecrawl login --browser or set FIRECRAWL_API_KEY in .env.local."
  else
    printf '%s\n' "Firecrawl is optional. Get an API key from https://www.firecrawl.dev/ when you want web research helpers."
    record_summary deferred "Firecrawl ownership" "Firecrawl CLI is unavailable; set FIRECRAWL_API_KEY or rerun bootstrap later"
  fi
  setup_camofox_browser
  printf '%s\n' "Start Camofox only when needed with a loopback/auth wrapper:"
  printf '%s\n' "  CAMOFOX_ACCESS_KEY=\$(openssl rand -hex 24) scripts/start-camofox-browser.sh"
fi

if [ "$INCLUDE_DEV_TOOLS" -eq 1 ]; then
  install_npm_global ruflo ruflo@latest "RuFlo advisory CLI"
fi

printf '%s\n' "Bootstrap check complete. Run agentic-trader setup-status --json for machine-readable readiness."
render_summary
