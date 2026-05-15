#!/usr/bin/env bash
set -Eeuo pipefail

SONAR_HOST_URL="${SONAR_HOST_URL:-http://localhost:9000}"
SONAR_CONTAINER_NAME="${SONARQUBE_CONTAINER_NAME:-sonarqube}"

detect_db_password_mismatch() {
	docker logs "${SONAR_CONTAINER_NAME}" --tail 240 2>&1 \
		| grep -qi 'password authentication failed for user "sonar"'
}

detect_invalid_jwt_secret() {
	docker logs "${SONAR_CONTAINER_NAME}" --tail 240 2>&1 \
		| grep -qi 'Illegal base64 character'
}

if command -v docker >/dev/null 2>&1; then
	docker ps --filter "name=^sonarqube$" --filter "name=^sonarqube-db$" \
		--format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
fi

if command -v curl >/dev/null 2>&1; then
	echo
	curl -fsS "${SONAR_HOST_URL}/api/system/status" || {
		echo "SonarQube did not respond at ${SONAR_HOST_URL}" >&2
		if command -v docker >/dev/null 2>&1 && detect_db_password_mismatch; then
			cat >&2 <<'EOF'

Detected a local SonarQube/PostgreSQL password mismatch in recent logs.
Repair without deleting local Sonar history:

  pnpm run sonar:repair-db-password

If you use a custom SONAR_POSTGRES_PASSWORD, export the same value before repair
and start.
EOF
		elif command -v docker >/dev/null 2>&1 && detect_invalid_jwt_secret; then
			cat >&2 <<'EOF'

Detected an invalid SONAR_AUTH_JWTBASE64HS256SECRET value in recent logs.
Unset the variable to use the repository local-dev default, or generate one:

  export SONAR_AUTH_JWTBASE64HS256SECRET="$(openssl rand -base64 32)"
  pnpm run sonar:start
EOF
		fi
		exit 1
	}
	echo
fi
