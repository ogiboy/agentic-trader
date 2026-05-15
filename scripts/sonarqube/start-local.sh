#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="${SONARQUBE_COMPOSE_FILE:-${REPO_ROOT}/scripts/sonarqube/docker-compose.sonarqube.yml}"
SONAR_HOST_URL="${SONAR_HOST_URL:-http://localhost:9000}"
START_TIMEOUT_SECONDS="${SONARQUBE_START_TIMEOUT_SECONDS:-90}"
SONAR_CONTAINER_NAME="${SONARQUBE_CONTAINER_NAME:-sonarqube}"

detect_db_password_mismatch() {
	docker logs "${SONAR_CONTAINER_NAME}" --tail 240 2>&1 \
		| grep -qi 'password authentication failed for user "sonar"'
}

detect_invalid_jwt_secret() {
	docker logs "${SONAR_CONTAINER_NAME}" --tail 240 2>&1 \
		| grep -qi 'Illegal base64 character'
}

print_repair_hint() {
	cat >&2 <<'EOF'

Detected a local SonarQube/PostgreSQL password mismatch.

This usually happens when the existing Docker volume was initialized with an
older SONAR_POSTGRES_PASSWORD value. PostgreSQL keeps that stored user password
when the container is restarted, so changing compose defaults or shell env later
does not update the existing database user.

Repair without deleting local Sonar history:

  pnpm run sonar:repair-db-password

If you intentionally use a custom SONAR_POSTGRES_PASSWORD, export the same value
before running both commands.

Destructive last resort, only if you accept losing local Sonar history:

  docker compose -f scripts/sonarqube/docker-compose.sonarqube.yml down -v
EOF
}

print_jwt_secret_hint() {
	cat >&2 <<'EOF'

Detected an invalid SONAR_AUTH_JWTBASE64HS256SECRET value.

Recent SonarQube versions expect this value to be Base64 encoded. Unset the
variable to use the repository's local-dev default, or generate your own:

  export SONAR_AUTH_JWTBASE64HS256SECRET="$(openssl rand -base64 32)"
  pnpm run sonar:start
EOF
}

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
echo "Local SonarQube is starting at ${SONAR_HOST_URL}"

deadline=$((SECONDS + START_TIMEOUT_SECONDS))
while ((SECONDS < deadline)); do
	if response="$(curl -fsS "${SONAR_HOST_URL}/api/system/status" 2>/dev/null)"; then
		if grep -q '"status":"UP"' <<<"${response}"; then
			echo "Local SonarQube is ready at ${SONAR_HOST_URL}"
			exit 0
		fi
	fi

	container_state="$(docker inspect -f '{{.State.Status}}' "${SONAR_CONTAINER_NAME}" 2>/dev/null || true)"
	if [[ "${container_state}" == "exited" || "${container_state}" == "dead" ]]; then
		if detect_db_password_mismatch; then
			print_repair_hint
		elif detect_invalid_jwt_secret; then
			print_jwt_secret_hint
		else
			echo "SonarQube container stopped before becoming ready. Recent logs:" >&2
			docker logs "${SONAR_CONTAINER_NAME}" --tail 80 >&2 || true
		fi
		exit 1
	fi

	sleep 3
done

echo "Timed out waiting for local SonarQube to become ready at ${SONAR_HOST_URL}." >&2
if detect_db_password_mismatch; then
	print_repair_hint
elif detect_invalid_jwt_secret; then
	print_jwt_secret_hint
else
	echo "Current container status:" >&2
	docker ps --filter "name=^${SONAR_CONTAINER_NAME}$" \
		--format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" >&2 || true
	echo "Recent logs:" >&2
	docker logs "${SONAR_CONTAINER_NAME}" --tail 80 >&2 || true
fi
exit 1
