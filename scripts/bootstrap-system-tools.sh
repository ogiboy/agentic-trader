#!/usr/bin/env sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
YES=0
DRY_RUN=0
CORE_ONLY=0
INCLUDE_DEV_TOOLS=0
INCLUDE_BROWSER_TOOLS=0

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
  --include-browser-tools   Offer optional Camofox browser dependency install.
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

ask_yes() {
  prompt=$1
  if [ "$YES" -eq 1 ]; then
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
    return 0
  fi
  printf '✗ %s not found\n' "$label"
  if ask_yes "Install $label with Homebrew ($formula)?"; then
    require_homebrew || return 1
    run_cmd brew install "$formula"
  fi
}

install_npm_global() {
  command_name=$1
  package_name=$2
  label=$3
  if has_cmd "$command_name"; then
    printf '✓ %s found at %s\n' "$label" "$(command -v "$command_name")"
    return 0
  fi
  printf '✗ %s not found\n' "$label"
  if ! has_cmd npm; then
    printf '%s\n' "npm is required before installing $label." >&2
    return 0
  fi
  if ask_yes "Install $label globally with npm ($package_name)?"; then
    run_cmd npm install -g "$package_name"
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
        printf '%s\n' "Ensure $target_dir appears before stale global installs in PATH."
      fi
      return 0
    fi
    printf '✓ agentic-trader already resolves at %s\n' "$resolved_entrypoint"
    return 0
  fi
  if [ ! -x "$entrypoint" ]; then
    printf '%s\n' "agentic-trader entrypoint is not installed yet. Run make setup first, then rerun make setup-path or make bootstrap."
    return 0
  fi
  if ask_yes "Create/update $target so agentic-trader works from any shell?"; then
    run_cmd mkdir -p "$target_dir"
    if [ "$DRY_RUN" -eq 1 ]; then
      printf '+ ln -sf %s %s\n' "$entrypoint" "$target"
    else
      ln -sf "$entrypoint" "$target"
    fi
    printf '%s\n' "Ensure $target_dir is in PATH."
  fi
}

setup_camofox_browser() {
  camofox_dir="$ROOT_DIR/tools/camofox-browser"
  if [ ! -f "$camofox_dir/package.json" ]; then
    printf '%s\n' "Camofox browser helper is not present under tools/camofox-browser."
    return 0
  fi
  if [ -d "$camofox_dir/node_modules" ]; then
    printf '✓ Camofox browser dependencies appear installed\n'
    return 0
  fi
  printf '%s\n' "Camofox dependency install is local and skips browser downloads by default."
  if ask_yes "Install optional Camofox browser helper dependencies now?"; then
    run_cmd pnpm --dir "$camofox_dir" install --ignore-scripts
  fi
  printf '%s\n' "Camoufox browser binary download is separate and can be large."
  if ask_yes "Download/update the Camoufox browser binary now?"; then
    run_cmd pnpm --dir "$camofox_dir" run fetch:browser
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
    fi
  fi
fi
install_brew_tool pnpm pnpm "pnpm"
setup_agentic_trader_path

if [ "$CORE_ONLY" -eq 0 ]; then
  install_brew_tool ollama ollama "Ollama"
  if has_cmd ollama; then
    printf '%s\n' "Use agentic-trader model-service status/start/pull to inspect or run app-managed Ollama."
  fi
  install_npm_global firecrawl firecrawl-cli "Firecrawl CLI"
  if has_cmd firecrawl; then
    printf '%s\n' "Firecrawl needs auth before use: run firecrawl login --browser or set FIRECRAWL_API_KEY in .env.local."
  else
    printf '%s\n' "Firecrawl is optional. Get an API key from https://www.firecrawl.dev/ when you want web research helpers."
  fi
fi

if [ "$INCLUDE_BROWSER_TOOLS" -eq 1 ]; then
  setup_camofox_browser
  printf '%s\n' "Start Camofox only when needed with a loopback/auth wrapper:"
  printf '%s\n' "  CAMOFOX_ACCESS_KEY=\$(openssl rand -hex 24) scripts/start-camofox-browser.sh"
fi

if [ "$INCLUDE_DEV_TOOLS" -eq 1 ]; then
  install_npm_global ruflo ruflo@latest "RuFlo advisory CLI"
fi

printf '%s\n' "Bootstrap check complete. Run agentic-trader setup-status --json for machine-readable readiness."
