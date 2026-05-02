import stat

from agentic_trader.security import (
    append_private_text,
    ensure_private_directory,
    is_loopback_host,
    redact_sensitive_text,
    write_private_text,
)


def test_redact_sensitive_text_masks_common_secret_shapes(
    monkeypatch,
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


def test_private_runtime_artifact_helpers_use_owner_only_modes(tmp_path) -> None:
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
