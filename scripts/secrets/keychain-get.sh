#!/usr/bin/env bash
set -Eeuo pipefail

# usage prints the usage message for scripts/secrets/keychain-get.sh to stderr, describing the SERVICE [ACCOUNT] and --check modes and then returns 0.
usage() {
	cat >&2 <<'EOF'
Usage:
  scripts/secrets/keychain-get.sh SERVICE [ACCOUNT]
  scripts/secrets/keychain-get.sh --check SERVICE [ACCOUNT]

	Reads a generic password from macOS Keychain without writing it to disk.
	Use --check to verify that the item exists without printing the secret.
EOF
	return 0
}

MODE="get"
if [[ "${1:-}" == "--check" ]]; then
	MODE="check"
	shift
fi

SERVICE="${1:-}"
ACCOUNT="${2:-${USER:-}}"

if [[ -z "${SERVICE}" || -z "${ACCOUNT}" ]]; then
	usage
	exit 2
fi

if ! command -v security >/dev/null 2>&1; then
	echo "macOS 'security' command is required to read Keychain item '${SERVICE}'." >&2
	exit 1
fi

if [[ "${MODE}" == "check" ]]; then
	security find-generic-password -a "${ACCOUNT}" -s "${SERVICE}" -w >/dev/null
	echo "Keychain item is available: ${SERVICE}"
	exit 0
fi

security find-generic-password -a "${ACCOUNT}" -s "${SERVICE}" -w
