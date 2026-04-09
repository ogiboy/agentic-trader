# Project Profile

## Name

Agentic Trader

## What It Is

A strict, local-first, multi-agent paper trading system for Ollama-class models.

## What It Is Not

- not a generic chat agent project
- not an OpenClaw-style external orchestrator
- not a live broker system yet
- not a report generator pretending to be a trading engine

## Repository Intent

The project is trying to build a serious operator-facing trading runtime with:

- specialist agents
- deterministic execution guardrails
- inspectable state
- persistent journals and portfolio state
- CLI/TUI control surfaces
- replay and backtesting

## Current AI Workflow Outside The Repo

The human workflow may involve:

- ChatGPT for planning and review
- Codex or other coding tools for implementation assistance

Those tools are external helpers.
They must not redefine the architecture of this repository.

## Preferred Development Style

- local-first
- explicit over clever
- structured contracts over free-form outputs
- incremental implementation
- architecture-aware edits
- minimal breakage
- strong operator visibility

## Quality Bar

Changes should preserve:

- strict runtime safety
- replayability
- inspectability
- modularity
- operator clarity
