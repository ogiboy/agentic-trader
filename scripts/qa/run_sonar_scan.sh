#!/usr/bin/env bash
set -Eeuo pipefail

SCANNER="${1:-pysonar}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ARTIFACT_DIR="${SONAR_ARTIFACT_DIR:-${REPO_ROOT}/.ai/qa/artifacts/sonar}"
COVERAGE_XML="${SONAR_COVERAGE_XML:-${ARTIFACT_DIR}/coverage.xml}"
COVERAGE_LOG="${ARTIFACT_DIR}/coverage.log"
SCAN_LOG="${ARTIFACT_DIR}/${SCANNER}.log"

SONAR_HOST_URL="${SONAR_HOST_URL:-http://localhost:9000}"
SONAR_PROJECT_KEY="${SONAR_PROJECT_KEY:-agentic-trader}"
SONAR_PROJECT_NAME="${SONAR_PROJECT_NAME:-Agentic Trader}"
SONAR_ORGANIZATION="${SONAR_ORGANIZATION:-}"
SONAR_REGION="${SONAR_REGION:-}"
SONAR_SOURCES="${SONAR_SOURCES:-agentic_trader,main.py,webgui/src,docs/app,docs/components,docs/content,docs/lib,tui}"
SONAR_TESTS="${SONAR_TESTS:-tests}"
SONAR_TOKEN_KEYCHAIN_SERVICE="${SONAR_TOKEN_KEYCHAIN_SERVICE:-codex-sonarqube-token}"
SONAR_TOKEN_KEYCHAIN_ACCOUNT="${SONAR_TOKEN_KEYCHAIN_ACCOUNT:-${USER:-}}"

cd "${REPO_ROOT}"
mkdir -p "${ARTIFACT_DIR}"

resolve_token() {
	if [[ -n "${SONAR_TOKEN:-}" ]]; then
		return 0
	fi
	if command -v security >/dev/null 2>&1 && [[ -n "${SONAR_TOKEN_KEYCHAIN_ACCOUNT}" ]]; then
		SONAR_TOKEN="$(
			security find-generic-password \
				-a "${SONAR_TOKEN_KEYCHAIN_ACCOUNT}" \
				-s "${SONAR_TOKEN_KEYCHAIN_SERVICE}" \
				-w 2>/dev/null || true
		)"
		export SONAR_TOKEN
	fi
	if [[ -z "${SONAR_TOKEN:-}" ]]; then
		echo "SONAR_TOKEN is required. Set it in the environment or store it in macOS Keychain service '${SONAR_TOKEN_KEYCHAIN_SERVICE}'." >&2
		exit 1
	fi
	return 0
}

redacted_runner() {
	local -a command=("$@")
	local redacted_log="${SCAN_LOG}"
	local token_to_redact="${SONAR_TOKEN}"
	"${command[@]}" 2>&1 \
		| SONAR_TOKEN_REDACT="${token_to_redact}" perl -pe 'BEGIN { $t = $ENV{SONAR_TOKEN_REDACT} // ""; } if (length $t) { s/\Q$t\E/<redacted>/g }' \
		| tee "${redacted_log}"
	return 0
}

run_coverage() {
	if [[ "${SONAR_SKIP_COVERAGE:-0}" == "1" ]]; then
		echo "Skipping coverage generation because SONAR_SKIP_COVERAGE=1."
		return 0
	fi

	echo "Writing Python coverage XML to ${COVERAGE_XML}"
	poetry run python -m pytest -q -p no:cacheprovider \
		--cov=agentic_trader \
		--cov-report="xml:${COVERAGE_XML}" 2>&1 | tee "${COVERAGE_LOG}"
	return 0
}

run_pysonar() {
	local -a command=()
	if poetry run sh -c 'command -v pysonar >/dev/null 2>&1'; then
		command=(poetry run pysonar)
	elif command -v pysonar >/dev/null 2>&1; then
		command=(pysonar)
	elif [[ -x /Library/Frameworks/Python.framework/Versions/3.12/bin/pysonar ]]; then
		command=(/Library/Frameworks/Python.framework/Versions/3.12/bin/pysonar)
	else
		echo "pysonar is required. Run 'poetry install --with dev --extras dev' or install pysonar." >&2
		exit 1
	fi

	command+=(
		--sonar-host-url "${SONAR_HOST_URL}"
		--sonar-token "${SONAR_TOKEN}"
		--sonar-project-key "${SONAR_PROJECT_KEY}"
		--sonar-project-name "${SONAR_PROJECT_NAME}"
		--sonar-project-base-dir "${REPO_ROOT}"
		--sonar-sources "${SONAR_SOURCES}"
		--sonar-tests "${SONAR_TESTS}"
		--sonar-python-version "3.12"
	)
	if [[ -f "${COVERAGE_XML}" ]]; then
		command+=(--sonar-python-coverage-report-paths "${COVERAGE_XML}")
	fi
	if [[ -n "${SONAR_ORGANIZATION}" ]]; then
		command+=("-Dsonar.organization=${SONAR_ORGANIZATION}")
	fi
	if [[ -n "${SONAR_REGION}" ]]; then
		command+=("-Dsonar.region=${SONAR_REGION}")
	fi
	if [[ -n "${SONAR_BRANCH_NAME:-}" ]]; then
		command+=(--sonar-branch-name "${SONAR_BRANCH_NAME}")
	fi

	echo "Running pysonar for project '${SONAR_PROJECT_KEY}' at ${SONAR_HOST_URL}"
	redacted_runner "${command[@]}"
	return 0
}

run_npm_scanner() {
	local -a command=(
		pnpm exec sonar
		"-Dsonar.host.url=${SONAR_HOST_URL}"
		"-Dsonar.projectKey=${SONAR_PROJECT_KEY}"
		"-Dsonar.projectName=${SONAR_PROJECT_NAME}"
		"-Dsonar.python.coverage.reportPaths=${COVERAGE_XML}"
	)
	if [[ -n "${SONAR_ORGANIZATION}" ]]; then
		command+=("-Dsonar.organization=${SONAR_ORGANIZATION}")
	fi
	if [[ -n "${SONAR_REGION}" ]]; then
		command+=("-Dsonar.region=${SONAR_REGION}")
	fi
	if [[ -n "${SONAR_BRANCH_NAME:-}" ]]; then
		command+=("-Dsonar.branch.name=${SONAR_BRANCH_NAME}")
	fi

	echo "Running @sonar/scan for project '${SONAR_PROJECT_KEY}' at ${SONAR_HOST_URL}"
	redacted_runner "${command[@]}"
	return 0
}

resolve_token
run_coverage

case "${SCANNER}" in
	py|python|pysonar)
		SCAN_LOG="${ARTIFACT_DIR}/pysonar.log"
		run_pysonar
		;;
	js|node|npm|sonar)
		SCAN_LOG="${ARTIFACT_DIR}/sonar-npm.log"
		run_npm_scanner
		;;
	*)
		echo "Unknown scanner '${SCANNER}'. Use 'pysonar' or 'npm'." >&2
		exit 2
		;;
esac

echo "Sonar scanner log: ${SCAN_LOG}"
