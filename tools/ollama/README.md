# Ollama Tool Root

This directory is reserved for app-managed Ollama metadata and helper assets.
Agentic Trader should continue to detect host-system Ollama and app-owned
Ollama through `agentic-trader model-service status/start/stop/pull`.

Do not store downloaded model weights, provider secrets, or long-lived runtime
logs in this directory. Runtime state belongs under `runtime/model_service/`.
