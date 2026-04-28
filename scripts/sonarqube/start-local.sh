#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="${SONARQUBE_COMPOSE_FILE:-${REPO_ROOT}/scripts/sonarqube/docker-compose.sonarqube.yml}"

if ! command -v docker >/dev/null 2>&1; then
	echo "Docker is required to start local SonarQube." >&2
	exit 1
fi

if [[ ! -r "${COMPOSE_FILE}" ]]; then
	echo "SonarQube compose file is not readable: ${COMPOSE_FILE}" >&2
	exit 1
fi

if docker compose version >/dev/null 2>&1; then
	COMPOSE_COMMAND=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
	COMPOSE_COMMAND=(docker-compose)
else
	echo "Docker Compose is required. Install Docker Compose v2 or docker-compose." >&2
	exit 1
fi

"${COMPOSE_COMMAND[@]}" -f "${COMPOSE_FILE}" up -d
echo "Local SonarQube is starting at http://localhost:9000"
