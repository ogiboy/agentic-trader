#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="${SONARQUBE_COMPOSE_FILE:-${REPO_ROOT}/scripts/sonarqube/docker-compose.sonarqube.yml}"

if ! command -v docker >/dev/null 2>&1; then
	echo "Docker is required to start local SonarQube." >&2
	exit 1
fi

docker compose -f "${COMPOSE_FILE}" up -d
echo "Local SonarQube is starting at http://localhost:9000"
