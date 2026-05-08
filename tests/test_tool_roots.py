from pathlib import Path

from agentic_trader.system import tool_roots


def test_repo_tool_paths_are_under_tools_root() -> None:
    root = tool_roots.repo_root()

    assert tool_roots.tools_root() == root / "tools"
    assert tool_roots.repo_tool_path("camofox-browser") == root / "tools" / "camofox-browser"
    assert tool_roots.repo_tool_path("ollama") == root / "tools" / "ollama"
    assert tool_roots.repo_tool_path("firecrawl") == root / "tools" / "firecrawl"


def test_resolve_configured_tool_path_keeps_absolute_path() -> None:
    absolute = Path("/tmp/agentic-tool")

    assert (
        tool_roots.resolve_configured_tool_path(
            absolute,
            default_tool="camofox-browser",
        )
        == absolute
    )


def test_resolve_configured_tool_path_uses_repo_root_for_relative_path() -> None:
    assert tool_roots.resolve_configured_tool_path(
        "tools/camofox-browser",
        default_tool="camofox-browser",
    ) == tool_roots.repo_root() / "tools" / "camofox-browser"


def test_repo_tool_manifests_are_valid_json() -> None:
    for tool_id in ("camofox-browser", "ollama", "firecrawl"):
        manifest = tool_roots.read_repo_tool_manifest(tool_id)
        assert manifest is not None
        assert manifest["id"] == tool_id
        assert "entrypoints" in manifest
        assert "secret" not in str(manifest).lower()
