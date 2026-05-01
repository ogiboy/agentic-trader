#!/usr/bin/env sh
set -eu

if ! command -v uv >/dev/null 2>&1; then
	echo "uv is required for Agentic Trader Python setup. Install uv before running pnpm run install:python." >&2
	exit 1
fi

# Local daily development is pinned to Python 3.13. The package metadata keeps
# a wider supported range, and CI can still sync against the minimum version.
uv sync --locked --python 3.13 --all-extras --group dev
