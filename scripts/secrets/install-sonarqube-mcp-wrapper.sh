#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
INSTALL_PATH="${SONARQUBE_MCP_WRAPPER_PATH:-${HOME}/.local/bin/codex-sonarqube-mcp}"
CANONICAL_SCRIPT="${REPO_ROOT}/scripts/secrets/run-sonarqube-mcp.sh"
FALLBACK_SCRIPT="${HOME}/agentic-trader/scripts/secrets/run-sonarqube-mcp.sh"

mkdir -p "$(dirname "${INSTALL_PATH}")"

escape_sed_replacement() {
	printf '%s' "$1" | sed 's/[\/&]/\\&/g'
}

cat >"${INSTALL_PATH}" <<'EOF'
#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT="${AGENTIC_TRADER_SONAR_MCP_SCRIPT:-__CANONICAL_SCRIPT__}"
FALLBACK_SCRIPT="__FALLBACK_SCRIPT__"

if [[ ! -x "${SCRIPT}" && -x "${FALLBACK_SCRIPT}" ]]; then
	SCRIPT="${FALLBACK_SCRIPT}"
fi

if [[ ! -x "${SCRIPT}" ]]; then
	echo "SonarQube MCP launcher not found. Set AGENTIC_TRADER_SONAR_MCP_SCRIPT or reinstall from the repo." >&2
	exit 1
fi

exec "${SCRIPT}" "$@"
EOF

sed -i.bak \
	-e "s/__CANONICAL_SCRIPT__/$(escape_sed_replacement "${CANONICAL_SCRIPT}")/g" \
	-e "s/__FALLBACK_SCRIPT__/$(escape_sed_replacement "${FALLBACK_SCRIPT}")/g" \
	"${INSTALL_PATH}"
rm -f "${INSTALL_PATH}.bak"
chmod +x "${INSTALL_PATH}"
echo "Installed SonarQube MCP wrapper at ${INSTALL_PATH}"
