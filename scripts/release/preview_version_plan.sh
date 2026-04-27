#!/usr/bin/env bash
set -euo pipefail

set +e
tag="$(
  poetry run semantic-release --noop version --print-tag 2>/tmp/semantic-release-preview.log \
    | grep -E '^v[0-9]+(\.[0-9]+){2}([-.+][0-9A-Za-z.-]+)?$' \
    | tail -n 1
)"
status=$?
set -e

if [ "$status" -ne 0 ]; then
  tag=""
fi

python scripts/release/version_plan.py --semantic-tag "$tag" --format summary
