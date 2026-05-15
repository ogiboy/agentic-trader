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


def test_local_tool_definitions_expose_runtime_consumers_and_fallbacks() -> None:
    definitions = {
        definition.tool_id: definition
        for definition in tool_roots.iter_local_tool_definitions()
    }

    assert tuple(definitions) == ("ollama", "firecrawl", "camofox-browser")
    assert definitions["ollama"].status_tool_id == "ollama_cli"
    assert "model-service" in definitions["ollama"].consumers
    assert definitions["ollama"].fallback_order[0] == "app_managed_repo_config"
    assert definitions["firecrawl"].status_tool_id == "firecrawl_cli"
    assert "researchd" in definitions["firecrawl"].consumers
    assert "pure_python_or_js_fetcher" in definitions["firecrawl"].fallback_order
    assert definitions["camofox-browser"].status_tool_id == "camofox_browser"
    assert "camofox-service" in definitions["camofox-browser"].consumers
    assert definitions["camofox-browser"].fallback_order[0] == "repo_tools"
    assert "pnpm --dir tools/camofox-browser install --ignore-scripts" in definitions[
        "camofox-browser"
    ].install_hint
    assert "npm install" not in definitions["camofox-browser"].install_hint


def test_manifest_notes_are_safe_and_include_entrypoints() -> None:
    notes = tool_roots.local_tool_manifest_notes("camofox-browser")

    assert "local_tool_id=camofox-browser" in notes
    assert any(note.startswith("fallback_order=") for note in notes)
    assert any(note == "start=agentic-trader camofox-service start" for note in notes)
    assert "secret" not in " ".join(notes).lower()


def test_local_tool_status_payload_matches_registry_contract() -> None:
    payload = tool_roots.local_tool_status_payload("firecrawl")

    assert payload["tool_id"] == "firecrawl"
    assert payload["tool_status_id"] == "firecrawl_cli"
    assert "researchd" in payload["tool_consumers"]
    assert "firecrawl_api_key" in payload["tool_fallback_order"]
    assert "firecrawl login" in str(payload["install_hint"])
    notes = payload["notes"]
    assert isinstance(notes, list)
    assert "local_tool_id=firecrawl" in notes
