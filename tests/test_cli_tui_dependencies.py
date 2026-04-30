from collections.abc import Mapping

import pytest

import agentic_trader.cli as cli


def _patch_node_tools(
    monkeypatch: pytest.MonkeyPatch,
    tools: Mapping[str, str | None],
) -> None:
    monkeypatch.setattr(cli.shutil, "which", lambda name: tools.get(name))


def test_tui_dependencies_require_tui_package_node_modules(tmp_path):
    root_dir = tmp_path
    tui_dir = root_dir / "tui"
    tui_dir.mkdir()
    (root_dir / "node_modules" / ".pnpm").mkdir(parents=True)

    assert not cli._tui_dependencies_installed(tui_dir, root_dir)

    (tui_dir / "node_modules").mkdir()

    assert cli._tui_dependencies_installed(tui_dir, root_dir)


def test_resolve_tui_node_commands_prefers_root_pnpm_workspace(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root_dir = tmp_path
    tui_dir = root_dir / "tui"
    tui_dir.mkdir()
    (root_dir / "pnpm-workspace.yaml").touch()
    _patch_node_tools(monkeypatch, {"pnpm": "/usr/bin/pnpm"})

    assert cli._resolve_tui_node_commands(tui_dir) == (
        ["/usr/bin/pnpm", "install"],
        ["/usr/bin/pnpm", "--filter", "agentic-trader-tui", "run", "start"],
        root_dir,
        "pnpm workspace",
    )


def test_resolve_tui_node_commands_uses_tui_pnpm_lock(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root_dir = tmp_path
    tui_dir = root_dir / "tui"
    tui_dir.mkdir()
    (tui_dir / "pnpm-lock.yaml").touch()
    _patch_node_tools(monkeypatch, {"pnpm": "/usr/bin/pnpm"})

    assert cli._resolve_tui_node_commands(tui_dir) == (
        ["/usr/bin/pnpm", "install"],
        ["/usr/bin/pnpm", "run", "start"],
        tui_dir,
        "pnpm",
    )


def test_resolve_tui_node_commands_uses_npm_ci_for_package_lock(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root_dir = tmp_path
    tui_dir = root_dir / "tui"
    tui_dir.mkdir()
    (tui_dir / "package-lock.json").touch()
    _patch_node_tools(monkeypatch, {"pnpm": None, "npm": "/usr/bin/npm"})

    assert cli._resolve_tui_node_commands(tui_dir) == (
        ["/usr/bin/npm", "install"],
        ["/usr/bin/npm", "run", "start"],
        tui_dir,
        "npm",
    )


def test_resolve_tui_node_commands_falls_back_to_npm_install(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root_dir = tmp_path
    tui_dir = root_dir / "tui"
    tui_dir.mkdir()
    _patch_node_tools(monkeypatch, {"pnpm": None, "npm": "/usr/bin/npm"})

    assert cli._resolve_tui_node_commands(tui_dir) == (
        ["/usr/bin/npm", "install", "--no-package-lock"],
        ["/usr/bin/npm", "run", "start"],
        tui_dir,
        "npm",
    )


def test_resolve_tui_node_commands_uses_yarn_lock(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root_dir = tmp_path
    tui_dir = root_dir / "tui"
    tui_dir.mkdir()
    (tui_dir / "yarn.lock").touch()
    _patch_node_tools(
        monkeypatch,
        {"pnpm": None, "npm": None, "yarn": "/usr/bin/yarn"},
    )

    assert cli._resolve_tui_node_commands(tui_dir) == (
        ["/usr/bin/yarn", "install", "--frozen-lockfile"],
        ["/usr/bin/yarn", "start"],
        tui_dir,
        "yarn",
    )


def test_resolve_tui_node_commands_falls_back_to_yarn_install(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root_dir = tmp_path
    tui_dir = root_dir / "tui"
    tui_dir.mkdir()
    _patch_node_tools(
        monkeypatch,
        {"pnpm": None, "npm": None, "yarn": "/usr/bin/yarn"},
    )

    assert cli._resolve_tui_node_commands(tui_dir) == (
        ["/usr/bin/yarn", "install", "--no-lockfile"],
        ["/usr/bin/yarn", "start"],
        tui_dir,
        "yarn",
    )


def test_resolve_tui_node_commands_returns_none_without_manager(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tui_dir = tmp_path / "tui"
    tui_dir.mkdir()
    _patch_node_tools(monkeypatch, {"pnpm": None, "npm": None, "yarn": None})

    assert cli._resolve_tui_node_commands(tui_dir) is None
