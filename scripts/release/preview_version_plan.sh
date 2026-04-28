#!/usr/bin/env bash
set -euo pipefail

stderr_log="$(mktemp "${TMPDIR:-/tmp}/semantic-release-preview.XXXXXX.log")"
trap 'rm -f "${stderr_log}"' EXIT

set +e
tag="$(
  poetry run semantic-release --noop version --print-tag 2>"${stderr_log}" \
    | grep -E '^v[0-9]+(\.[0-9]+){2}([-.+][0-9A-Za-z.-]+)?$' \
    | tail -n 1
)"
status=$?
set -e

if [[ "$status" -ne 0 ]]; then
  tag=""
fi

python scripts/release/version_plan.py --semantic-tag "$tag" --format summary
