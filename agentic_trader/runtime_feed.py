import json
from pathlib import Path

from agentic_trader.config import Settings
from agentic_trader.schemas import (
    ChatHistoryEntry,
    ResearchSnapshotRecord,
    ServiceEvent,
    ServiceStateSnapshot,
)


def service_state_path(settings: Settings) -> Path:
    return settings.runtime_dir / "service_state.json"


def service_events_path(settings: Settings) -> Path:
    return settings.runtime_dir / "service_events.jsonl"


def stop_request_path(settings: Settings) -> Path:
    return settings.runtime_dir / "service_stop_requested"


def chat_history_path(settings: Settings) -> Path:
    return settings.runtime_dir / "chat_history.jsonl"


def research_snapshots_path(settings: Settings) -> Path:
    return settings.runtime_dir / "research_snapshots.jsonl"


def research_latest_snapshot_path(settings: Settings) -> Path:
    return settings.runtime_dir / "research_latest_snapshot.json"


def write_service_state(settings: Settings, state: ServiceStateSnapshot) -> None:
    path = service_state_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(state.model_dump_json(indent=2), encoding="utf-8")


def read_service_state(settings: Settings) -> ServiceStateSnapshot | None:
    path = service_state_path(settings)
    if not path.exists():
        return None
    return ServiceStateSnapshot.model_validate_json(path.read_text(encoding="utf-8"))


def append_service_event(settings: Settings, event: ServiceEvent) -> None:
    path = service_events_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(event.model_dump_json())
        handle.write("\n")


def read_service_events(settings: Settings, *, limit: int = 20) -> list[ServiceEvent]:
    path = service_events_path(settings)
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    events: list[ServiceEvent] = []
    for line in lines[-limit:]:
        if not line.strip():
            continue
        events.append(ServiceEvent.model_validate(json.loads(line)))
    events.reverse()
    return events


def append_chat_history(settings: Settings, entry: ChatHistoryEntry) -> None:
    path = chat_history_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(entry.model_dump_json())
        handle.write("\n")


def read_chat_history(settings: Settings, *, limit: int = 20) -> list[ChatHistoryEntry]:
    path = chat_history_path(settings)
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    entries: list[ChatHistoryEntry] = []
    for line in lines[-limit:]:
        if not line.strip():
            continue
        entries.append(ChatHistoryEntry.model_validate(json.loads(line)))
    entries.reverse()
    return entries


def append_research_snapshot(
    settings: Settings, record: ResearchSnapshotRecord
) -> None:
    path = research_snapshots_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(record.model_dump_json())
        handle.write("\n")
    research_latest_snapshot_path(settings).write_text(
        record.model_dump_json(indent=2), encoding="utf-8"
    )


def read_research_snapshots(
    settings: Settings, *, limit: int = 20
) -> list[ResearchSnapshotRecord]:
    path = research_snapshots_path(settings)
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    records: list[ResearchSnapshotRecord] = []
    for line in lines[-limit:]:
        if not line.strip():
            continue
        records.append(ResearchSnapshotRecord.model_validate(json.loads(line)))
    records.reverse()
    return records


def read_latest_research_snapshot(settings: Settings) -> ResearchSnapshotRecord | None:
    latest_path = research_latest_snapshot_path(settings)
    if latest_path.exists():
        return ResearchSnapshotRecord.model_validate_json(
            latest_path.read_text(encoding="utf-8")
        )
    records = read_research_snapshots(settings, limit=1)
    return records[0] if records else None


def request_stop(settings: Settings) -> None:
    path = stop_request_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("stop\n", encoding="utf-8")


def stop_requested(settings: Settings) -> bool:
    return stop_request_path(settings).exists()


def clear_stop_request(settings: Settings) -> None:
    path = stop_request_path(settings)
    if path.exists():
        path.unlink()
