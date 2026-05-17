# Agentic Trader Camofox Browser Helper

This directory contains a trimmed, repo-local browser helper based on the
MIT-licensed `jo-inc/camofox-browser` project. Agentic Trader uses it as an
optional loopback-only research helper when Firecrawl/API providers are not
enough and a browser snapshot is explicitly needed.

Local policy:

- bind only to `127.0.0.1`, `localhost`, or `::1`
- require `CAMOFOX_ACCESS_KEY` or `CAMOFOX_API_KEY`
- keep crash telemetry disabled by default
- keep browser prewarm disabled by default; launch the browser on demand
- do not store raw scraped pages, broker secrets, provider secrets, or model
  outputs in this directory
- keep `node_modules/`, browser binaries, caches, logs, and runtime state
  untracked

Setup:

```sh
pnpm --dir tools/camofox-browser install --ignore-workspace --ignore-scripts
```

The browser binary download is separate and explicit:

```sh
pnpm --dir tools/camofox-browser --ignore-workspace run fetch:browser
```

Start through Agentic Trader rather than calling `node server.js` directly:

```sh
CAMOFOX_ACCESS_KEY="$(openssl rand -hex 24)" scripts/start-camofox-browser.sh
agentic-trader camofox-service status
```

The helper refuses non-loopback hosts without `CAMOFOX_ACCESS_KEY`, and
`NODE_ENV=production` requires that key even on loopback. Agentic Trader's
app-owned service path mirrors `CAMOFOX_API_KEY` into the local access key when
an explicit access key is not configured.

The helper is evidence infrastructure only. It must not mutate broker state,
runtime policy, live-trading gates, or proposal approval state.
