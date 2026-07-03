import json
import stat
from pathlib import Path

from pytest import MonkeyPatch

from agentic_trader.security import (
    append_private_text,
    ensure_private_directory,
    is_loopback_host,
    redact_sensitive_text,
    write_private_text,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _read_flat_workspace_overrides() -> dict[str, str]:
    overrides: dict[str, str] = {}
    in_overrides = False
    for line in (
        (REPO_ROOT / "pnpm-workspace.yaml").read_text(encoding="utf-8").splitlines()
    ):
        if line == "overrides:":
            in_overrides = True
            continue
        if in_overrides and line and not line.startswith(" "):
            break
        if in_overrides and line.startswith("  "):
            name, value = line.strip().split(": ", 1)
            overrides[name.strip('"')] = value.strip('"')
    return overrides


def test_node_security_overrides_stay_in_sync() -> None:
    package_overrides = json.loads(
        (REPO_ROOT / "package.json").read_text(encoding="utf-8")
    )["overrides"]
    workspace_overrides = _read_flat_workspace_overrides()

    assert package_overrides == workspace_overrides
    assert workspace_overrides["form-data"] == "4.0.6"
    assert workspace_overrides["hono"] == "4.12.25"
    assert workspace_overrides["undici"] == "7.28.0"
    assert workspace_overrides["vite"] == "8.0.16"


def test_redact_sensitive_text_masks_common_secret_shapes(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENTIC_TRADER_ALPACA_SECRET_KEY", "secret-from-env")

    text = (
        "AGENTIC_TRADER_ALPACA_SECRET_KEY=secret-from-env "
        "Authorization: Bearer abc.def.ghi "
        "https://example.test?api_key=secret-query"
    )

    redacted = redact_sensitive_text(text)

    assert "secret-from-env" not in redacted
    assert "abc.def.ghi" not in redacted
    assert "secret-query" not in redacted
    assert "<redacted>" in redacted


def test_redact_sensitive_text_strips_ansi_escape_sequences() -> None:
    text = "\x1b[38;5;208mfirecrawl\x1b[0m status"

    assert redact_sensitive_text(text) == "firecrawl status"


def test_private_runtime_artifact_helpers_use_owner_only_modes(tmp_path: Path) -> None:
    directory = tmp_path / "runtime"
    path = directory / "service_events.jsonl"

    ensure_private_directory(directory)
    write_private_text(path, "first\n")
    append_private_text(path, "second\n")

    assert path.read_text(encoding="utf-8") == "first\nsecond\n"
    assert stat.S_IMODE(directory.stat().st_mode) == 0o700
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_loopback_host_rejects_empty_all_interface_bind() -> None:
    assert is_loopback_host("") is False
    assert is_loopback_host("   ") is False
    assert is_loopback_host("localhost") is True
    assert is_loopback_host("127.0.0.1") is True
    assert is_loopback_host("0.0.0.0") is False
