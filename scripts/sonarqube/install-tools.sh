#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${REPO_ROOT}"

pnpm install --frozen-lockfile
uv sync --locked --all-extras --group dev

echo "Sonar scanner tools are available through:"
echo "  pnpm exec sonar"
echo "  uv run --locked --all-extras --group dev pysonar"
echo
echo "Local Docker scans use project key agentic-trader and Keychain service codex-sonarqube-token."
echo "Manual SonarCloud scans use project key ogiboy_agentic-trader and Keychain service codex-sonarcloud-token."
