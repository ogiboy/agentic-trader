#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
KEYCHAIN_SERVICE="${SONARQUBE_KEYCHAIN_SERVICE:-codex-sonarqube-token}"

echo "SonarQube MCP topology"
echo "repo: ${REPO_ROOT}"
echo "keychain service: ${KEYCHAIN_SERVICE}"

if ! command -v docker >/dev/null 2>&1; then
	echo "Docker is required to inspect local SonarQube and MCP containers." >&2
	exit 1
fi

"${REPO_ROOT}/scripts/secrets/keychain-get.sh" --check "${KEYCHAIN_SERVICE}"

echo
SONARQUBE_MCP_DRY_RUN=1 "${REPO_ROOT}/scripts/secrets/run-sonarqube-mcp.sh"

echo
echo "Local SonarQube server containers:"
docker ps --filter name='^/sonarqube$' --filter name='^/sonarqube-db$' \
	--format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'

echo
echo "Running mcp/sonarqube client containers:"
mapfile -t mcp_containers < <(docker ps --filter ancestor=mcp/sonarqube --format '{{.ID}}\t{{.Names}}\t{{.Status}}')
if ((${#mcp_containers[@]} == 0)); then
	echo "none"
else
	printf '%s\n' "${mcp_containers[@]}"
fi

if ((${#mcp_containers[@]} > 2)); then
	cat >&2 <<'EOF'

Warning: more than two mcp/sonarqube containers are running.
This usually means several Codex or VS Code MCP sessions are alive at the same time.
It is not the SonarQube server itself, but it can confuse QA. Restart inactive clients or
stop stale mcp/sonarqube containers only after confirming no active session depends on them.
EOF
fi
