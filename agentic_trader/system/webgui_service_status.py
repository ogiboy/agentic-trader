"""Status payload builders for the local Web GUI service."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

from agentic_trader.system.webgui_service_state import (
    WebGUIServiceState,
    WebGUIServiceStatus,
)

RuntimeStatusFields = tuple[str | None, Path | None, bool]
TailReader = Callable[[str | None, int], list[str]]
PortOwnerResolver = Callable[[str, int], int | None]
ProcessMatcher = Callable[[int], bool]
UrlBuilder = Callable[[str, int], str]
ReachabilityProbe = Callable[[str], tuple[bool, str]]


def status_url(
    *,
    app_state: WebGUIServiceState | None,
    state: WebGUIServiceState | None,
    default_url: str,
) -> str:
    if app_state is not None:
        return app_state.url
    if state is not None:
        return state.url
    return default_url


def status_message(
    *,
    package_available: bool,
    command_path: str | None,
    dependency_path: Path | None,
    app_state: WebGUIServiceState | None,
    state: WebGUIServiceState | None,
    reachable: bool,
    reachability_message: str,
) -> str:
    if not package_available:
        return "Web GUI package is missing."
    if command_path is None:
        return "node is not installed or not on PATH."
    if dependency_path is None:
        return "Web GUI dependencies are missing. Run pnpm install first."
    if app_state is not None and reachable:
        return "App-owned Web GUI is running."
    if state is not None and app_state is None:
        return "Recorded Web GUI state is stale or process ownership could not be verified."
    return reachability_message


def state_status(
    *,
    app_state: WebGUIServiceState | None,
    url: str,
    reachable: bool,
    runtime_fields: RuntimeStatusFields,
    state_path: Path,
    message: str,
    tail_reader: TailReader,
    tail_limit: int,
) -> WebGUIServiceStatus:
    command_path, dependency_path, package_available = runtime_fields
    stdout_log_path = app_state.stdout_log_path if app_state is not None else None
    stderr_log_path = app_state.stderr_log_path if app_state is not None else None
    return WebGUIServiceStatus(
        command_available=command_path is not None,
        command_path=command_path,
        package_available=package_available,
        dependency_available=dependency_path is not None,
        dependency_path=str(dependency_path) if dependency_path is not None else None,
        app_owned=app_state is not None,
        pid=app_state.pid if app_state is not None else None,
        host=app_state.host if app_state is not None else None,
        port=app_state.port if app_state is not None else None,
        url=url,
        service_reachable=reachable,
        stdout_log_path=stdout_log_path,
        stderr_log_path=stderr_log_path,
        stdout_tail=tail_reader(stdout_log_path, tail_limit),
        stderr_tail=tail_reader(stderr_log_path, tail_limit),
        state_path=str(state_path),
        message=message,
    )


def unverified_start_status(
    *,
    state: WebGUIServiceState,
    service_reachable: bool,
    runtime_fields: RuntimeStatusFields,
    state_path: Path,
    message: str,
    tail_reader: TailReader,
    tail_limit: int,
) -> WebGUIServiceStatus:
    command_path, dependency_path, package_available = runtime_fields
    return WebGUIServiceStatus(
        command_available=command_path is not None,
        command_path=command_path,
        package_available=package_available,
        dependency_available=dependency_path is not None,
        dependency_path=str(dependency_path) if dependency_path is not None else None,
        app_owned=False,
        pid=None,
        host=state.host,
        port=state.port,
        url=state.url,
        service_reachable=service_reachable,
        stdout_log_path=state.stdout_log_path,
        stderr_log_path=state.stderr_log_path,
        stdout_tail=tail_reader(state.stdout_log_path, tail_limit),
        stderr_tail=tail_reader(state.stderr_log_path, tail_limit),
        state_path=str(state_path),
        message=message,
    )


def external_status(
    *,
    default_host: str,
    ports: Iterable[int],
    runtime_fields: RuntimeStatusFields,
    state_path: Path,
    listen_port_owner_pid: PortOwnerResolver,
    process_looks_like_webgui: ProcessMatcher,
    url_for: UrlBuilder,
    reachability_probe: ReachabilityProbe,
) -> WebGUIServiceStatus | None:
    command_path, dependency_path, package_available = runtime_fields
    for port in ports:
        owner_pid = listen_port_owner_pid(default_host, port)
        if owner_pid is None or not process_looks_like_webgui(owner_pid):
            continue
        url = url_for(default_host, port)
        reachable, message = reachability_probe(url)
        if not reachable:
            continue
        return WebGUIServiceStatus(
            command_available=command_path is not None,
            command_path=command_path,
            package_available=package_available,
            dependency_available=dependency_path is not None,
            dependency_path=(
                str(dependency_path) if dependency_path is not None else None
            ),
            app_owned=False,
            pid=None,
            host=default_host,
            port=port,
            url=url,
            service_reachable=True,
            state_path=str(state_path),
            message=(
                "A Web GUI dev server is already reachable, but it was not "
                "started by webgui-service and will not be stopped by the app."
                if message == "Web GUI is reachable."
                else message
            ),
        )
    return None
