"""Persistent optional tool ownership decisions.

This module records operator intent for optional helper tools. It stores no
secrets, starts no services, and never installs dependencies; setup and runtime
surfaces use it to distinguish host-owned, app-owned, API/key-only, skipped,
and undecided helper tools.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, TypedDict

from pydantic import BaseModel

from agentic_trader.config import Settings
from agentic_trader.security import write_private_text
from agentic_trader.system.tool_roots import LocalToolId

OwnershipToolId = Literal["ollama", "firecrawl", "camofox"]
OwnershipMode = Literal[
    "undecided",
    "host-owned",
    "app-owned",
    "api-key-only",
    "skipped",
]

SCHEMA_VERSION = "tool-ownership/v1"
OWNERSHIP_TOOL_IDS: tuple[OwnershipToolId, ...] = (
    "ollama",
    "firecrawl",
    "camofox",
)
OWNERSHIP_MODES: tuple[OwnershipMode, ...] = (
    "undecided",
    "host-owned",
    "app-owned",
    "api-key-only",
    "skipped",
)


class ToolOwnershipUpdate(TypedDict, total=False):
    """Write payload for one optional tool ownership decision."""

    mode: OwnershipMode
    source: str
    updated_at: str


class ToolOwnershipDecision(BaseModel):
    """Operator intent for one optional tool."""

    tool: OwnershipToolId
    mode: OwnershipMode = "undecided"
    source: str = "default"
    updated_at: str | None = None
    note: str


class ToolOwnershipPayload(BaseModel):
    """JSON payload shared by setup, CLI, Web GUI, and TUI."""

    schema_version: str = SCHEMA_VERSION
    state_path: str
    updated_at: str | None = None
    decisions: list[ToolOwnershipDecision]
    decisions_by_tool: dict[str, ToolOwnershipDecision]


def _utc_now_iso() -> str:
    """
    Return the current UTC time as an ISO-8601 formatted string.
    
    Returns:
        str: Current UTC time in ISO-8601 format with UTC timezone offset.
    """
    return datetime.now(timezone.utc).isoformat()


def tool_ownership_path(settings: Settings) -> Path:
    """
    Get the file path used to store owner-only tool ownership state.
    
    Returns:
        Path: Path to the `tool-ownership.json` file inside the runtime `setup` directory.
    """

    return settings.runtime_dir / "setup" / "tool-ownership.json"


def normalize_ownership_tool(tool: str) -> OwnershipToolId:
    """
    Convert a user or registry tool identifier to the canonical ownership tool ID.
    
    Returns:
        The ownership tool ID corresponding to the input (one of "ollama", "firecrawl", "camofox").
    
    Raises:
        ValueError: If the provided `tool` is not a recognized ownership tool identifier.
            The exception message is formatted as "unknown_tool_ownership_id:<tool>".
    """

    if tool == "camofox-browser":
        return "camofox"
    if tool in OWNERSHIP_TOOL_IDS:
        return tool  # type: ignore[return-value]
    msg = f"unknown_tool_ownership_id:{tool}"
    raise ValueError(msg)


def ownership_tool_for_local_tool(tool_id: LocalToolId) -> OwnershipToolId:
    """Map a registry local-tool ID to the ownership-decision ID."""

    return normalize_ownership_tool(tool_id)


def validate_ownership_mode(mode: str) -> OwnershipMode:
    """
    Ensure the input string is a supported ownership mode.
    
    Returns:
        The validated value as an `OwnershipMode`.
    
    Raises:
        ValueError: If `mode` is not one of the supported ownership modes; the error message lists the allowed modes excluding `"undecided"`.
    """

    if mode in OWNERSHIP_MODES:
        return mode  # type: ignore[return-value]
    msg = (
        "ownership mode must be one of: "
        + ", ".join(mode for mode in OWNERSHIP_MODES if mode != "undecided")
    )
    raise ValueError(msg)


def ownership_note(tool: OwnershipToolId, mode: OwnershipMode) -> str:
    """
    Provide an operator-facing explanatory note describing the meaning and implications of a tool's ownership mode.
    
    Parameters:
        tool (OwnershipToolId): The normalized ownership tool identifier (e.g., "ollama", "firecrawl", "camofox").
        mode (OwnershipMode): The ownership mode whose explanation is requested.
    
    Returns:
        str: A human-readable note explaining the operator-facing meaning of the specified ownership mode. For the combination of `tool == "firecrawl"` and `mode == "app-owned"`, a more specific Firecrawl-focused note is returned.
    """

    notes: dict[OwnershipMode, str] = {
        "undecided": (
            "No ownership decision is recorded yet; setup may report degraded "
            "readiness instead of claiming this helper."
        ),
        "host-owned": (
            "Use a host-managed tool or endpoint; app lifecycle commands must "
            "not install, start, stop, update, or delete it."
        ),
        "app-owned": (
            "The app may manage repo/local loopback helper setup or service "
            "state only through explicit lifecycle commands."
        ),
        "api-key-only": (
            "Use ignored environment/keychain credentials only; no CLI install "
            "or local service ownership is implied."
        ),
        "skipped": (
            "Keep this helper disabled or degraded; core paper-first workflows "
            "must remain understandable without it."
        ),
    }
    if tool == "firecrawl" and mode == "app-owned":
        return (
            "Firecrawl app-owned uses the repo dependency path first; credentials "
            "still belong in ignored env/keychain state and host CLI fallback "
            "requires host-owned mode."
        )
    return notes[mode]


def _default_decision(tool: OwnershipToolId) -> ToolOwnershipDecision:
    """
    Create the default undecided ownership decision for a given tool.
    
    Parameters:
        tool (OwnershipToolId): The ownership tool identifier to produce a decision for.
    
    Returns:
        ToolOwnershipDecision: A decision with mode "undecided", source "default", updated_at set to None, and a generated note describing the undecided state for the tool.
    """
    return ToolOwnershipDecision(
        tool=tool,
        mode="undecided",
        source="default",
        updated_at=None,
        note=ownership_note(tool, "undecided"),
    )


def _decision_from_record(
    tool: OwnershipToolId,
    record: object,
) -> ToolOwnershipDecision:
    """
    Convert a raw record (typically from loaded JSON) into a ToolOwnershipDecision for the given tool.
    
    Parameters:
        tool (OwnershipToolId): The ownership tool identifier to associate with the decision.
        record (object): Raw record parsed from the persisted payload; expected to be a dict with optional keys
            `"mode"`, `"source"`, and `"updated_at"`. If `record` is not a dict, a default undecided decision is returned.
    
    Returns:
        ToolOwnershipDecision: A decision populated from the record where:
            - `mode` is the validated ownership mode (falls back to `"undecided"` on invalid input),
            - `source` defaults to `"file"` when absent,
            - `updated_at` is included only if it is a string,
            - `note` is generated for the tool and mode.
    """
    if not isinstance(record, dict):
        return _default_decision(tool)
    raw_mode = str(record.get("mode") or "undecided")
    try:
        mode = validate_ownership_mode(raw_mode)
    except ValueError:
        mode = "undecided"
    source = str(record.get("source") or "file")
    updated_at = record.get("updated_at")
    return ToolOwnershipDecision(
        tool=tool,
        mode=mode,
        source=source,
        updated_at=updated_at if isinstance(updated_at, str) else None,
        note=ownership_note(tool, mode),
    )


def read_tool_ownership_payload(settings: Settings) -> ToolOwnershipPayload:
    """
    Load the persisted tool ownership payload and return a complete payload with defaults for any missing tools.
    
    If the runtime JSON file exists, attempts to read and parse it; a malformed file or read error is treated as if no decisions were recorded. The returned ToolOwnershipPayload contains the file path, the payload-level `updated_at` (or `None`), a `decisions` list with one ToolOwnershipDecision for every supported tool (missing or invalid records produce an `undecided` default), and `decisions_by_tool` mapping tool IDs to their decisions.
    
    Returns:
        ToolOwnershipPayload: The assembled payload including `state_path`, `updated_at`, `decisions`, and `decisions_by_tool`.
    """

    path = tool_ownership_path(settings)
    updated_at: str | None = None
    records: dict[str, object] = {}
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                updated = payload.get("updated_at")
                updated_at = updated if isinstance(updated, str) else None
                raw_records = payload.get("decisions")
                records = raw_records if isinstance(raw_records, dict) else {}
        except (OSError, json.JSONDecodeError):
            records = {}

    decisions = [
        _decision_from_record(tool, records.get(tool))
        for tool in OWNERSHIP_TOOL_IDS
    ]
    decisions_by_tool = {decision.tool: decision for decision in decisions}
    return ToolOwnershipPayload(
        state_path=str(path),
        updated_at=updated_at,
        decisions=decisions,
        decisions_by_tool=decisions_by_tool,
    )


def ownership_mode_for_tool(settings: Settings, tool: str) -> OwnershipMode:
    """
    Get the stored ownership mode for the given tool, defaulting to `undecided` when no decision is recorded.
    
    Parameters:
        settings (Settings): Runtime settings used to locate the ownership state file.
        tool (str): Tool identifier to normalize (accepts ownership and some registry/local IDs, e.g. "camofox" or "camofox-browser").
    
    Returns:
        OwnershipMode: The persisted ownership mode for the tool; `undecided` if no decision is present.
    """

    tool_id = normalize_ownership_tool(tool)
    payload = read_tool_ownership_payload(settings)
    decision = payload.decisions_by_tool.get(tool_id)
    return decision.mode if decision is not None else "undecided"


def write_tool_ownership(
    settings: Settings,
    updates: dict[str, str],
    *,
    source: str = "cli",
) -> ToolOwnershipPayload:
    """
    Merge and persist operator ownership decisions for optional helper tools.
    
    Applies the provided updates to the existing owner-only runtime payload, removing decisions set to "undecided", recording the source and update timestamps, writing the resulting JSON to the runtime state file, and returning the refreshed payload.
    
    Parameters:
        settings (Settings): Runtime settings used to locate the owner-only state file.
        updates (dict[str, str]): Mapping from a tool identifier (user or registry form; will be normalized) to an ownership mode string (validated against supported modes). Entries with mode "undecided" will be removed from persisted records.
        source (str): Origin label to record for applied updates (defaults to "cli").
    
    Returns:
        ToolOwnershipPayload: The refreshed payload read from persistent storage after the write, containing the current decisions and per-tool metadata.
    """

    existing = read_tool_ownership_payload(settings)
    now = _utc_now_iso()
    records: dict[str, ToolOwnershipUpdate] = {
        decision.tool: {
            "mode": decision.mode,
            "source": decision.source,
            "updated_at": decision.updated_at or now,
        }
        for decision in existing.decisions
        if decision.mode != "undecided"
    }
    for raw_tool, raw_mode in updates.items():
        tool = normalize_ownership_tool(raw_tool)
        mode = validate_ownership_mode(raw_mode)
        if mode == "undecided":
            records.pop(tool, None)
            continue
        records[tool] = {
            "mode": mode,
            "source": source,
            "updated_at": now,
        }
    payload = {
        "schema_version": SCHEMA_VERSION,
        "updated_at": now,
        "decisions": records,
    }
    write_private_text(
        tool_ownership_path(settings),
        json.dumps(payload, indent=2, sort_keys=True),
    )
    return read_tool_ownership_payload(settings)
