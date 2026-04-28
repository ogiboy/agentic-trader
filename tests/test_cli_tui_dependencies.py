from agentic_trader.cli import _tui_dependencies_installed


def test_tui_dependencies_require_tui_package_node_modules(tmp_path):
    root_dir = tmp_path
    tui_dir = root_dir / "tui"
    tui_dir.mkdir()
    (root_dir / "node_modules" / ".pnpm").mkdir(parents=True)

    assert not _tui_dependencies_installed(tui_dir, root_dir)

    (tui_dir / "node_modules").mkdir()

    assert _tui_dependencies_installed(tui_dir, root_dir)
