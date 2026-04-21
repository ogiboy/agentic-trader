from pathlib import Path

from scripts.qa import smoke_qa


def test_claim_artifacts_dir_uses_unique_suffix_for_existing_label(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(smoke_qa, "ARTIFACTS_ROOT", tmp_path)

    first = smoke_qa._claim_artifacts_dir("smoke-fixed")
    second = smoke_qa._claim_artifacts_dir("smoke-fixed")

    assert first == tmp_path / "smoke-fixed"
    assert second == tmp_path / "smoke-fixed-2"
    assert first.is_dir()
    assert second.is_dir()
