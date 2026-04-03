import json
from pathlib import Path

from agentic_trader.config import Settings
from agentic_trader.schemas import ServiceEvent, ServiceStateSnapshot


def service_state_path(settings: Settings) -> Path:
    return settings.runtime_dir / "service_state.json"


def service_events_path(settings: Settings) -> Path:
    return settings.runtime_dir / "service_events.jsonl"


def stop_request_path(settings: Settings) -> Path:
    return settings.runtime_dir / "service_stop_requested"


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
