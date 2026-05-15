#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="${SONARQUBE_COMPOSE_FILE:-${REPO_ROOT}/scripts/sonarqube/docker-compose.sonarqube.yml}"
DB_CONTAINER_NAME="${SONARQUBE_DB_CONTAINER_NAME:-sonarqube-db}"
SONAR_DB_NAME="${SONAR_POSTGRES_DB:-sonar}"
SONAR_DB_USER="${SONAR_POSTGRES_USER:-sonar}"
SONAR_DB_PASSWORD="${SONAR_POSTGRES_PASSWORD:-sonar-local-password}"

if ! command -v docker >/dev/null 2>&1; then
	echo "Docker is required to repair the local SonarQube database password." >&2
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

if [[ "$(docker inspect -f '{{.State.Running}}' "${DB_CONTAINER_NAME}" 2>/dev/null || true)" != "true" ]]; then
	echo "Starting the local SonarQube PostgreSQL container..." >&2
	"${COMPOSE_COMMAND[@]}" -f "${COMPOSE_FILE}" up -d db
fi

echo "Waiting for the local SonarQube PostgreSQL container..." >&2
for _ in {1..30}; do
	if docker exec -u postgres "${DB_CONTAINER_NAME}" pg_isready -U "${SONAR_DB_USER}" -d "${SONAR_DB_NAME}" >/dev/null 2>&1; then
		break
	fi
	sleep 2
done

if ! docker exec -u postgres "${DB_CONTAINER_NAME}" pg_isready -U "${SONAR_DB_USER}" -d "${SONAR_DB_NAME}" >/dev/null 2>&1; then
	echo "PostgreSQL did not become ready in ${DB_CONTAINER_NAME}." >&2
	exit 1
fi

docker exec -i -u postgres "${DB_CONTAINER_NAME}" psql -U "${SONAR_DB_USER}" -d "${SONAR_DB_NAME}" \
	-v ON_ERROR_STOP=1 \
	-v sonar_user="${SONAR_DB_USER}" \
	-v sonar_password="${SONAR_DB_PASSWORD}" <<'SQL'
ALTER USER :"sonar_user" WITH PASSWORD :'sonar_password';
SQL

echo "Local SonarQube PostgreSQL password is aligned with the current SONAR_POSTGRES_PASSWORD."
echo "Run pnpm run sonar:start to start SonarQube."
