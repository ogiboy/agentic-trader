#!/usr/bin/env bash
set -Eeuo pipefail

SCANNER="${1:-pysonar}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ARTIFACT_DIR="${SONAR_ARTIFACT_DIR:-${REPO_ROOT}/.ai/qa/artifacts/sonar}"
COVERAGE_XML="${SONAR_COVERAGE_XML:-${ARTIFACT_DIR}/coverage.xml}"
COVERAGE_LOG="${ARTIFACT_DIR}/coverage.log"
JAVASCRIPT_LCOV="${SONAR_JAVASCRIPT_LCOV:-${ARTIFACT_DIR}/javascript/lcov.info}"
JAVASCRIPT_COVERAGE_LOG="${ARTIFACT_DIR}/javascript-coverage.log"
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

# resolve_token resolves the Sonar authentication token used by the script.
# It ensures SONAR_TOKEN is set (exported) by using the existing environment value or, if absent, by attempting a macOS Keychain lookup; if the token cannot be obtained it prints an error and exits with status 1.
resolve_token() {
	if [[ -z "${SONAR_TOKEN:-}" ]] && command -v security >/dev/null 2>&1 && [[ -n "${SONAR_TOKEN_KEYCHAIN_ACCOUNT}" ]]; then
		SONAR_TOKEN="$(
			security find-generic-password \
				-a "${SONAR_TOKEN_KEYCHAIN_ACCOUNT}" \
				-s "${SONAR_TOKEN_KEYCHAIN_SERVICE}" \
				-w 2>/dev/null || true
		)"
	fi
	if [[ -z "${SONAR_TOKEN:-}" ]]; then
		echo "SONAR_TOKEN is required. Set it in the environment or store it in macOS Keychain service '${SONAR_TOKEN_KEYCHAIN_SERVICE}'." >&2
		exit 1
	fi
	export SONAR_TOKEN
	return 0
}

# redacted_runner executes a command, replacing occurrences of `SONAR_TOKEN` in its combined stdout/stderr with `<redacted>` and teeing the redacted output to `SCAN_LOG` and to stdout.
redacted_runner() {
	local -a command=("$@")
	local -r redacted_log="${SCAN_LOG:-${ARTIFACT_DIR}/${SCANNER}.log}"
	local token_to_redact="${SONAR_TOKEN}"
	"${command[@]}" 2>&1 \
		| SONAR_TOKEN_REDACT="${token_to_redact}" perl -pe 'BEGIN { $t = $ENV{SONAR_TOKEN_REDACT} // ""; } if (length $t) { s/\Q$t\E/<redacted>/go }' \
		| tee "${redacted_log}"
	return 0
}

# run_coverage generates Python coverage XML at ${COVERAGE_XML} and saves pytest output to ${COVERAGE_LOG}; if SONAR_SKIP_COVERAGE=1 it prints a skipping message and returns immediately.
run_coverage() {
	if [[ "${SONAR_SKIP_COVERAGE:-0}" == "1" ]]; then
		echo "Skipping coverage generation because SONAR_SKIP_COVERAGE=1."
		return 0
	fi

	echo "Writing Python coverage XML to ${COVERAGE_XML}"
	uv run --locked --all-extras --group dev python -m pytest -q -p no:cacheprovider \
		--cov=agentic_trader \
		--cov-report="xml:${COVERAGE_XML}" 2>&1 | tee "${COVERAGE_LOG}"
	return 0
}

run_javascript_coverage() {
	if [[ "${SONAR_SKIP_COVERAGE:-0}" == "1" ]]; then
		echo "Skipping JavaScript coverage generation because SONAR_SKIP_COVERAGE=1."
		return 0
	fi
	mkdir -p "$(dirname "${JAVASCRIPT_LCOV}")"
	if ! SONAR_JAVASCRIPT_COVERAGE_DIR="$(dirname "${JAVASCRIPT_LCOV}")" pnpm run --silent test:node:coverage 2>&1 | tee "${JAVASCRIPT_COVERAGE_LOG}"; then
		echo "JavaScript coverage failed. See ${JAVASCRIPT_COVERAGE_LOG}." >&2
		exit 1
	fi
	return 0
}

# run_pysonar runs the Python Sonar scanner (`pysonar`) with project and environment-derived arguments and dispatches execution through `redacted_runner`. It fails and exits with status 1 if no usable `pysonar` executable is found; when present, it includes the coverage XML, organization, region, and branch parameters only if those environment variables/files are set.
run_pysonar() {
	local -a command=()
	if uv run --locked --all-extras --group dev sh -c 'command -v pysonar >/dev/null 2>&1'; then
		command=(uv run --locked --all-extras --group dev pysonar)
	elif command -v pysonar >/dev/null 2>&1; then
		command=(pysonar)
	elif [[ -x /Library/Frameworks/Python.framework/Versions/3.12/bin/pysonar ]]; then
		command=(/Library/Frameworks/Python.framework/Versions/3.12/bin/pysonar)
	else
		echo "pysonar is required. Run 'pnpm run install:python' or install pysonar." >&2
		exit 1
	fi

	command+=(
		--sonar-host-url "${SONAR_HOST_URL}"
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
	if [[ -f "${JAVASCRIPT_LCOV}" ]]; then
		command+=("-Dsonar.javascript.lcov.reportPaths=${JAVASCRIPT_LCOV}")
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

# run_npm_scanner builds and runs `pnpm exec sonar` with configured Sonar properties (host, project key/name, optional organization/region/branch, and Python coverage report path) and streams redacted scanner output to the scan log.
run_npm_scanner() {
	local -a command=(
		pnpm exec sonar
		"-Dsonar.host.url=${SONAR_HOST_URL}"
		"-Dsonar.projectKey=${SONAR_PROJECT_KEY}"
		"-Dsonar.projectName=${SONAR_PROJECT_NAME}"
	)
	if [[ -f "${COVERAGE_XML}" ]]; then
		command+=("-Dsonar.python.coverage.reportPaths=${COVERAGE_XML}")
	fi
	if [[ -f "${JAVASCRIPT_LCOV}" ]]; then
		command+=("-Dsonar.javascript.lcov.reportPaths=${JAVASCRIPT_LCOV}")
	fi
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
run_javascript_coverage

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
		echo "Unknown scanner '${SCANNER}'. Use one of: py, python, pysonar, js, node, npm, sonar." >&2
		exit 2
		;;
esac

echo "Sonar scanner log: ${SCAN_LOG}"
