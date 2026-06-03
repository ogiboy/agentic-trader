from __future__ import annotations

import io
import os
import time
from pathlib import Path
from typing import Any, cast

import pexpect  # type: ignore[import-untyped]

from scripts.qa.smoke_qa_modules.common import (
    EXIT_WAIT_SECONDS,
    PROMPT_PRESS_ENTER,
    PROMPT_SELECT_ACTION,
    RENDER_SECONDS,
    TUI_READY_PATTERNS,
    artifact_path,
    command_display,
    operator_noise_marker,
    output_has_traceback,
    write_artifact,
)
from scripts.qa.smoke_qa_modules.models import CheckResult, SmokeContext


def spawn_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("TERM", "xterm-256color")
    return env


def drain_child(child: Any, seconds: float, *, pexpect_module: Any = pexpect) -> None:
    deadline = time.monotonic() + seconds
    while child.isalive() and time.monotonic() < deadline:
        try:
            child.expect([pexpect_module.EOF, pexpect_module.TIMEOUT], timeout=0.25)
        except OSError:
            break


def close_interactive_child(child: Any, *, pexpect_module: Any = pexpect) -> str:
    if not child.isalive():
        return "exited_after_render"
    try:
        child.send("q")
        exit_method = "sent_q"
    except OSError:
        return "exited_before_q"
    drain_child(child, EXIT_WAIT_SECONDS, pexpect_module=pexpect_module)

    if not child.isalive():
        return exit_method
    try:
        child.sendcontrol("c")
        exit_method = "sent_ctrl_c"
    except OSError:
        return "exited_before_ctrl_c"
    drain_child(child, EXIT_WAIT_SECONDS, pexpect_module=pexpect_module)

    if child.isalive():
        child.terminate(force=True)
        time.sleep(0.2)
        return "force_terminated"
    return exit_method


def write_interactive_artifact(
    artifact: Path,
    display_command: str,
    exit_method: str,
    child: Any,
    output: str,
    *,
    repo_root: Path,
) -> None:
    write_artifact(
        artifact,
        f"$ {display_command}\n"
        f"cwd: {repo_root}\n"
        f"exit_method: {exit_method}\n"
        f"exitstatus: {child.exitstatus}\n"
        f"signalstatus: {child.signalstatus}\n\n"
        f"CAPTURE:\n{output}\n",
    )


def interactive_check_result(
    name: str,
    artifact: Path,
    exit_method: str,
    child: Any,
    output: str,
) -> CheckResult:
    if not output.strip():
        return CheckResult(
            name=name,
            passed=False,
            details=f"{exit_method}; no_visible_output",
            artifact=str(artifact),
        )
    if output_has_traceback(output):
        return CheckResult(
            name=name,
            passed=False,
            details=f"{exit_method}; traceback_detected",
            artifact=str(artifact),
        )
    noise_marker = operator_noise_marker(output)
    if noise_marker is not None:
        return CheckResult(
            name=name,
            passed=False,
            details=f"{exit_method}; raw_operator_noise={noise_marker}",
            artifact=str(artifact),
        )
    ctrl_c_exit = exit_method == "sent_ctrl_c" and child.exitstatus == 130
    if child.exitstatus not in (None, 0) and not ctrl_c_exit:
        return CheckResult(
            name=name,
            passed=False,
            details=f"{exit_method}; exit_code={child.exitstatus}",
            artifact=str(artifact),
        )
    if exit_method == "force_terminated":
        return CheckResult(
            name=name,
            passed=False,
            details=exit_method,
            artifact=str(artifact),
        )
    return CheckResult(
        name=name,
        passed=True,
        details=exit_method,
        artifact=str(artifact),
    )


def wait_for_tui_ready(child: Any, *, timeout: int) -> str:
    matched_index = cast(int, child.expect(list(TUI_READY_PATTERNS), timeout=timeout))
    return TUI_READY_PATTERNS[matched_index]


def _spawn_child(
    command: str,
    args: list[str],
    *,
    repo_root: Path,
    pexpect_module: Any,
    timeout: int,
    dimensions: tuple[int, int],
) -> Any:
    return pexpect_module.spawn(
        command,
        args=args,
        cwd=str(repo_root),
        env=cast(Any, spawn_env()),
        encoding="utf-8",
        timeout=timeout,
        dimensions=dimensions,
    )


def _terminate_if_alive(child: Any | None) -> None:
    if child is not None and child.isalive():
        child.terminate(force=True)


def _tui_ready_failure(
    *,
    name: str,
    artifact: Path,
    display_command: str,
    repo_root: Path,
    output: str,
    failure: str,
    details: str,
    exception: Exception,
    timeout: int | None = None,
) -> CheckResult:
    timeout_line = f"timeout: {timeout}\n" if timeout is not None else ""
    write_artifact(
        artifact,
        f"$ {display_command}\n"
        f"cwd: {repo_root}\n"
        f"failure: {failure}\n"
        f"{timeout_line}"
        f"exception: {exception}\n\n"
        f"CAPTURE:\n{output}\n",
    )
    return CheckResult(
        name=name,
        passed=False,
        details=details,
        artifact=str(artifact),
    )


def _tui_exception_result(
    *,
    name: str,
    artifact: Path,
    display_command: str,
    repo_root: Path,
    output: str,
    exception: Exception,
) -> CheckResult:
    write_artifact(
        artifact,
        f"$ {display_command}\n"
        f"cwd: {repo_root}\n"
        f"exception: {exception}\n\n"
        f"CAPTURE:\n{output}\n",
    )
    return CheckResult(
        name=name,
        passed=False,
        details=f"exception={exception}",
        artifact=str(artifact),
    )


def _capture_open_and_quit(
    *,
    name: str,
    artifact: Path,
    display_command: str,
    command: str,
    args: list[str],
    repo_root: Path,
    pexpect_module: Any,
    timeout: int,
    log: io.StringIO,
) -> CheckResult:
    child: Any | None = None
    try:
        active_child = _spawn_child(
            command,
            args,
            repo_root=repo_root,
            pexpect_module=pexpect_module,
            timeout=timeout,
            dimensions=(36, 120),
        )
        child = active_child
        active_child.logfile_read = log
        ready_signal = wait_for_tui_ready(active_child, timeout=timeout)
        drain_child(active_child, RENDER_SECONDS, pexpect_module=pexpect_module)
        exit_method = close_interactive_child(
            active_child, pexpect_module=pexpect_module
        )
        active_child.close(force=False)
        return _open_and_quit_success_result(
            name=name,
            artifact=artifact,
            display_command=display_command,
            repo_root=repo_root,
            child=active_child,
            output=log.getvalue(),
            exit_method=exit_method,
            ready_signal=ready_signal,
        )
    except pexpect_module.TIMEOUT as exc:
        _terminate_if_alive(child)
        return _tui_ready_failure(
            name=name,
            artifact=artifact,
            display_command=display_command,
            repo_root=repo_root,
            output=log.getvalue(),
            failure="tui_ready_timeout",
            details="tui_ready_timeout",
            exception=exc,
            timeout=timeout,
        )
    except pexpect_module.EOF as exc:
        return _tui_ready_failure(
            name=name,
            artifact=artifact,
            display_command=display_command,
            repo_root=repo_root,
            output=log.getvalue(),
            failure="tui_ready_eof",
            details="tui_ready_eof",
            exception=exc,
        )
    except Exception as exc:
        _terminate_if_alive(child)
        return _tui_exception_result(
            name=name,
            artifact=artifact,
            display_command=display_command,
            repo_root=repo_root,
            output=log.getvalue(),
            exception=exc,
        )


def _open_and_quit_success_result(
    *,
    name: str,
    artifact: Path,
    display_command: str,
    repo_root: Path,
    child: Any,
    output: str,
    exit_method: str,
    ready_signal: str,
) -> CheckResult:
    write_interactive_artifact(
        artifact,
        display_command,
        exit_method,
        child,
        output,
        repo_root=repo_root,
    )
    result = interactive_check_result(name, artifact, exit_method, child, output)
    if not result.passed:
        return result
    return CheckResult(
        name=result.name,
        passed=True,
        details=f"{result.details}; ready={ready_signal}",
        artifact=result.artifact,
    )


def run_tui_open_and_quit(
    context: SmokeContext,
    name: str,
    command: str,
    args: list[str],
    *,
    repo_root: Path,
    pexpect_module: Any = pexpect,
    display: str | None = None,
    timeout: int = 20,
) -> CheckResult:
    artifact = artifact_path(context, name)
    display_command = display or command_display([command, *args])
    log = io.StringIO()
    return _capture_open_and_quit(
        name=name,
        artifact=artifact,
        display_command=display_command,
        command=command,
        args=args,
        repo_root=repo_root,
        pexpect_module=pexpect_module,
        timeout=timeout,
        log=log,
    )


def _perform_rich_navigation(child: Any, *, timeout: int) -> None:
    child.expect(PROMPT_SELECT_ACTION, timeout=timeout)
    child.sendline("6")
    child.expect("Review And Trace", timeout=timeout)
    child.sendline("3")
    child.expect(PROMPT_PRESS_ENTER, timeout=timeout)
    child.sendline("")

    child.expect(PROMPT_SELECT_ACTION, timeout=timeout)
    child.sendline("5")
    child.expect("Research And Memory", timeout=timeout)
    child.sendline("2")
    child.expect("Runtime Events|Recent Runs", timeout=timeout)
    child.expect(PROMPT_PRESS_ENTER, timeout=timeout)
    child.sendline("")
    child.expect("Research And Memory", timeout=timeout)
    child.sendline("3")
    child.expect(PROMPT_PRESS_ENTER, timeout=timeout)
    child.sendline("")

    child.expect(PROMPT_SELECT_ACTION, timeout=timeout)
    child.sendline("4")
    child.expect("Portfolio And Risk", timeout=timeout)
    child.sendline("1")
    child.expect("Portfolio", timeout=timeout)
    child.expect(PROMPT_PRESS_ENTER, timeout=timeout)
    child.sendline("")
    child.expect("Portfolio And Risk", timeout=timeout)
    child.sendline("4")
    child.expect(PROMPT_PRESS_ENTER, timeout=timeout)
    child.sendline("")

    child.expect(PROMPT_SELECT_ACTION, timeout=timeout)
    child.sendline("7")


def _finish_scripted_navigation(child: Any, *, pexpect_module: Any) -> str:
    drain_child(child, EXIT_WAIT_SECONDS, pexpect_module=pexpect_module)
    exit_method = "scripted_navigation"
    if child.isalive():
        child.sendcontrol("c")
        exit_method = "scripted_navigation_ctrl_c"
        drain_child(child, EXIT_WAIT_SECONDS, pexpect_module=pexpect_module)
    if child.isalive():
        child.terminate(force=True)
        exit_method = "force_terminated"
    return exit_method


def _capture_rich_navigation(
    *,
    name: str,
    artifact: Path,
    display_command: str,
    command: str,
    repo_root: Path,
    pexpect_module: Any,
    timeout: int,
    log: io.StringIO,
) -> CheckResult:
    child: Any | None = None
    try:
        active_child = _spawn_child(
            command,
            ["menu"],
            repo_root=repo_root,
            pexpect_module=pexpect_module,
            timeout=timeout,
            dimensions=(40, 140),
        )
        child = active_child
        active_child.logfile_read = log
        wait_for_tui_ready(active_child, timeout=timeout)
        _perform_rich_navigation(active_child, timeout=timeout)
        exit_method = _finish_scripted_navigation(
            active_child, pexpect_module=pexpect_module
        )
        active_child.close(force=False)
        output = log.getvalue()
        write_interactive_artifact(
            artifact,
            display_command,
            exit_method,
            active_child,
            output,
            repo_root=repo_root,
        )
        return interactive_check_result(
            name, artifact, exit_method, active_child, output
        )
    except Exception as exc:
        _terminate_if_alive(child)
        return _tui_exception_result(
            name=name,
            artifact=artifact,
            display_command=display_command,
            repo_root=repo_root,
            output=log.getvalue(),
            exception=exc,
        )


def run_rich_menu_deep_navigation(
    context: SmokeContext,
    command: str,
    *,
    repo_root: Path,
    pexpect_module: Any = pexpect,
    timeout: int = 20,
) -> CheckResult:
    name = "rich_menu_deep_navigation"
    artifact = artifact_path(context, name)
    display_command = command_display([command, "menu"])
    log = io.StringIO()
    return _capture_rich_navigation(
        name=name,
        artifact=artifact,
        display_command=display_command,
        command=command,
        repo_root=repo_root,
        pexpect_module=pexpect_module,
        timeout=timeout,
        log=log,
    )
