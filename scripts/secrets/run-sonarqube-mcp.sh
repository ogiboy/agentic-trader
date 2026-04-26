#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
KEYCHAIN_GET="${REPO_ROOT}/scripts/secrets/keychain-get.sh"

SONARQUBE_URL="${SONARQUBE_URL:-${SONARQUBE_CLOUD_URL:-}}"
SONARQUBE_IDE_PORT="${SONARQUBE_IDE_PORT:-64120}"
SONARQUBE_KEYCHAIN_ACCOUNT="${SONARQUBE_KEYCHAIN_ACCOUNT:-${USER:-}}"

if [[ -z "${SONARQUBE_URL}" ]]; then
	SONARQUBE_URL="http://host.docker.internal:9000"
fi

if [[ -z "${SONARQUBE_KEYCHAIN_SERVICE:-}" ]]; then
	if [[ -n "${SONARQUBE_ORG:-}" ]]; then
		SONARQUBE_KEYCHAIN_SERVICE="codex-sonarcloud-token"
	else
		SONARQUBE_KEYCHAIN_SERVICE="codex-sonarqube-token"
	fi
fi

if [[ -z "${SONARQUBE_TOKEN:-}" ]]; then
	SONARQUBE_TOKEN="$("${KEYCHAIN_GET}" "${SONARQUBE_KEYCHAIN_SERVICE}" "${SONARQUBE_KEYCHAIN_ACCOUNT}")"
	export SONARQUBE_TOKEN
fi

export SONARQUBE_URL SONARQUBE_IDE_PORT
if [[ -n "${SONARQUBE_ORG:-}" ]]; then
	export SONARQUBE_ORG
fi

DOCKER_ARGS=(
	run
	--init
	-i
	--rm
	-e
	SONARQUBE_TOKEN
	-e
	SONARQUBE_URL
	-e
	SONARQUBE_IDE_PORT
)

if [[ -n "${SONARQUBE_ORG:-}" ]]; then
	DOCKER_ARGS+=(-e SONARQUBE_ORG)
fi

DOCKER_ARGS+=(mcp/sonarqube)

if [[ "${SONARQUBE_MCP_DRY_RUN:-0}" == "1" ]]; then
	printf 'docker'
	for arg in "${DOCKER_ARGS[@]}"; do
		printf ' %q' "${arg}"
	done
	printf '\n'
	printf 'SONARQUBE_URL=%s\n' "${SONARQUBE_URL}"
	printf 'SONARQUBE_ORG=%s\n' "${SONARQUBE_ORG:-}"
	printf 'SONARQUBE_KEYCHAIN_SERVICE=%s\n' "${SONARQUBE_KEYCHAIN_SERVICE}"
	printf 'SONARQUBE_TOKEN=<redacted>\n'
	exit 0
fi

exec docker "${DOCKER_ARGS[@]}"
