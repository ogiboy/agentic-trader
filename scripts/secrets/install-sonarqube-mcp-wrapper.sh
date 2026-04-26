#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
INSTALL_PATH="${SONARQUBE_MCP_WRAPPER_PATH:-${HOME}/.local/bin/codex-sonarqube-mcp}"
CANONICAL_SCRIPT="${REPO_ROOT}/scripts/secrets/run-sonarqube-mcp.sh"
FALLBACK_SCRIPT="${HOME}/agentic-trader/scripts/secrets/run-sonarqube-mcp.sh"

mkdir -p "$(dirname "${INSTALL_PATH}")"

cat >"${INSTALL_PATH}" <<EOF
#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT="\${AGENTIC_TRADER_SONAR_MCP_SCRIPT:-${CANONICAL_SCRIPT}}"
FALLBACK_SCRIPT="${FALLBACK_SCRIPT}"

if [[ ! -x "\${SCRIPT}" && -x "\${FALLBACK_SCRIPT}" ]]; then
	SCRIPT="\${FALLBACK_SCRIPT}"
fi

if [[ ! -x "\${SCRIPT}" ]]; then
	echo "SonarQube MCP launcher not found. Set AGENTIC_TRADER_SONAR_MCP_SCRIPT or reinstall from the repo." >&2
	exit 1
fi

exec "\${SCRIPT}" "\$@"
EOF

chmod +x "${INSTALL_PATH}"
echo "Installed SonarQube MCP wrapper at ${INSTALL_PATH}"
