from __future__ import annotations

import json
from collections.abc import Callable, Collection, Mapping
from pathlib import Path
from typing import Any, NoReturn, Protocol, TypeVar, cast

import pytest

T = TypeVar("T")


class HasPid(Protocol):
    pid: int


def constant(value: T) -> Callable[..., T]:
    def _inner(*_args: object, **_kwargs: object) -> T:
        return value

    return _inner


def approx(
    expected: object,
    *,
    rel: object | None = None,
    abs_tol: object | None = None,
    nan_ok: bool = False,
) -> object:
    approx_func = cast(Callable[..., object], vars(pytest)["approx"])
    return approx_func(expected, rel=rel, abs=abs_tol, nan_ok=nan_ok)


def raising(error: Exception) -> Callable[..., NoReturn]:
    def _raise(*_args: object, **_kwargs: object) -> NoReturn:
        raise error

    return _raise


def json_object(payload: str) -> dict[str, Any]:
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise AssertionError("expected JSON object")
    return cast(dict[str, Any], data)


def json_list(payload: str) -> list[Any]:
    data = json.loads(payload)
    if not isinstance(data, list):
        raise AssertionError("expected JSON list")
    return cast(list[Any], data)


def empty_int_list(*_args: object, **_kwargs: object) -> list[int]:
    return []


def pid_is(expected_pid: int) -> Callable[[int], bool]:
    def _matches(pid: int) -> bool:
        return pid == expected_pid

    return _matches


def pid_not_in(values: Collection[int]) -> Callable[[int], bool]:
    def _matches(pid: int) -> bool:
        return pid not in values

    return _matches


def pid_in(values: Collection[int]) -> Callable[[int], bool]:
    def _matches(pid: int) -> bool:
        return pid in values

    return _matches


def state_pid_is(expected_pid: int) -> Callable[[HasPid], bool]:
    def _matches(state: HasPid) -> bool:
        return state.pid == expected_pid

    return _matches


def state_pid_is_alive(
    expected_pid: int,
    alive: Collection[int],
) -> Callable[[HasPid], bool]:
    def _matches(state: HasPid) -> bool:
        return state.pid == expected_pid and expected_pid in alive

    return _matches


def port_available_except(*blocked_ports: int) -> Callable[[str, int], bool]:
    blocked = set(blocked_ports)

    def _available(_host: str, port: int) -> bool:
        return port not in blocked

    return _available


def port_available_only(*available_ports: int) -> Callable[[str, int], bool]:
    available = set(available_ports)

    def _available(_host: str, port: int) -> bool:
        return port in available

    return _available


def listen_owner_for(
    mapping: dict[int, int],
) -> Callable[[str, int], int | None]:
    def _owner(_host: str, port: int) -> int | None:
        return mapping.get(port)

    return _owner


def loopback_ports_for(
    mapping: Mapping[int, set[int]],
) -> Callable[[int], set[int]]:
    def _ports(pid: int) -> set[int]:
        return mapping.get(pid, set())

    return _ports


def no_sleep(_seconds: float) -> None:
    return None


def process_command_line(value: str | None) -> Callable[[int], str | None]:
    def _command_line(_pid: int) -> str | None:
        return value

    return _command_line


def process_command_line_for(
    mapping: Mapping[int, str],
) -> Callable[[int], str | None]:
    def _command_line(pid: int) -> str | None:
        return mapping.get(pid)

    return _command_line


def process_cwd(value: Path | None) -> Callable[[int], Path | None]:
    def _cwd(_pid: int) -> Path | None:
        return value

    return _cwd


def process_cwd_for(
    mapping: Mapping[int, Path],
) -> Callable[[int], Path | None]:
    def _cwd(pid: int) -> Path | None:
        return mapping.get(pid)

    return _cwd


def reachable_message(message: str) -> Callable[[str], tuple[bool, str]]:
    def _reachable(url: str) -> tuple[bool, str]:
        return True, message.format(url=url)

    return _reachable


def unreachable_message(message: str) -> Callable[[str], tuple[bool, str]]:
    def _unreachable(_url: str) -> tuple[bool, str]:
        return False, message

    return _unreachable


def ollama_tags_available(
    api_root: str, timeout_seconds: float = 2.0
) -> tuple[bool, list[str], str]:
    _ = timeout_seconds
    return True, ["qwen3:8b"], f"{api_root} reachable"


def ollama_tags_reachable(
    _api_root: str, timeout_seconds: float = 2.0
) -> tuple[bool, list[str], str]:
    _ = timeout_seconds
    return True, ["qwen3:8b"], "Ollama is reachable."


def ollama_tags_unavailable(
    api_root: str, timeout_seconds: float = 2.0
) -> tuple[bool, list[str], str]:
    _ = timeout_seconds
    return False, [], f"{api_root} unavailable"
