from __future__ import annotations

from pathlib import Path

from scripts.qa.modularity_i18n_audit import build_report, parse_args


def test_parse_args_accepts_pnpm_separator() -> None:
    args = parse_args(["--", "--top", "5"])

    assert args.top == 5


def test_audit_reports_docs_locale_parity(tmp_path: Path) -> None:
    en = tmp_path / "docs" / "content" / "docs" / "en"
    tr = tmp_path / "docs" / "content" / "docs" / "tr"
    en.mkdir(parents=True)
    tr.mkdir(parents=True)
    (en / "index.mdx").write_text("# Home\n", encoding="utf-8")
    (en / "extra.mdx").write_text("# Extra\n", encoding="utf-8")
    (tr / "index.mdx").write_text("# Ana sayfa\n", encoding="utf-8")

    report = build_report(repo_root=tmp_path, roots=("docs",))

    assert report.docs_locale_parity.english_only == ("extra.mdx",)
    assert report.docs_locale_parity.turkish_only == ()


def test_audit_reports_repeated_helpers_and_copy_candidates(tmp_path: Path) -> None:
    package = tmp_path / "agentic_trader"
    package.mkdir()
    for index in range(3):
        (package / f"module_{index}.py").write_text(
            "from collections.abc import Mapping\n"
            "def _object_mapping(value: object) -> Mapping[str, object]:\n"
            "    return value if isinstance(value, Mapping) else {}\n",
            encoding="utf-8",
        )
    (package / "cli.py").write_text(
        "def render() -> None:\n"
        "    table.add_column('Runtime Status')\n",
        encoding="utf-8",
    )

    report = build_report(repo_root=tmp_path, roots=("agentic_trader",))

    assert [helper.name for helper in report.repeated_helpers] == ["_object_mapping"]
    assert report.copy_candidates
    assert report.copy_candidates[0].excerpt == "table.add_column('Runtime Status')"
