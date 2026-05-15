# Local Tool Roots

`tools/` is for optional local helper infrastructure that Agentic Trader can
inspect or start explicitly. These helpers are not broker/runtime authorities
and must not receive broker secrets, mutate trading policy, or bypass
paper-first gates.

Current and planned roots:

- `camofox-browser/`: optional loopback browser helper source plus
  `agentic-tool.json`. Start through
  `scripts/start-camofox-browser.sh`, `make start-camofox`, or
  `agentic-trader camofox-service start` with `CAMOFOX_ACCESS_KEY` or
  `CAMOFOX_API_KEY`. Install Node deps with `make setup-camofox`, which uses
  `pnpm --dir tools/camofox-browser install --ignore-scripts`; download the
  browser binary separately with `make fetch-camofox`.
- `ollama/`: app-managed Ollama manifest, model-service metadata, and local
  model defaults. Do not vendor model weights here.
- `firecrawl/`: Firecrawl manifest, SDK/CLI handoff metadata, and fallback
  policy. Do not store API keys here.

Resolution order for runtime integrations:

1. repo-owned tool root with an explicit wrapper or adapter
2. user-configured host-system command or endpoint
3. safe built-in Python/JS fallback when available
4. degraded readiness with a clear operator message
