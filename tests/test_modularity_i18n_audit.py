from __future__ import annotations

from pathlib import Path

from scripts.qa.modularity_i18n_audit import (
    build_report,
    parse_args,
    should_fail_gate,
)


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
    assert should_fail_gate(report, fail_on_findings=True)
    assert not should_fail_gate(report, fail_on_findings=False)


def test_audit_reports_repeated_helpers_and_copy_candidates(tmp_path: Path) -> None:
    """
    Verifies build_report detects repeated helper functions across modules and identifies copy candidates.

    Asserts that the repeated helpers include "_object_mapping" and that there is at least one copy candidate whose excerpt is "table.add_column('Runtime Status')".
    """
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
        "def render() -> None:\n" "    table.add_column('Runtime Status')\n",
        encoding="utf-8",
    )

    report = build_report(repo_root=tmp_path, roots=("agentic_trader",))

    assert [helper.name for helper in report.repeated_helpers] == ["_object_mapping"]
    assert report.copy_candidates
    assert report.copy_candidates[0].excerpt == "table.add_column('Runtime Status')"


def test_default_audit_scope_includes_project_docs_and_tool_js(
    tmp_path: Path,
) -> None:
    ai_file = tmp_path / ".ai" / "decisions.instructions.md"
    ai_file.parent.mkdir(parents=True)
    ai_file.write_text("\n".join(["# Decision"] * 501), encoding="utf-8")
    artifact_file = tmp_path / ".ai" / "qa" / "artifacts" / "coverage.md"
    artifact_file.parent.mkdir(parents=True)
    artifact_file.write_text("\n".join(["# Generated"] * 900), encoding="utf-8")
    tool_file = tmp_path / "tools" / "browser-helper" / "server.js"
    tool_file.parent.mkdir(parents=True)
    tool_file.write_text("\n".join(["export const x = 1;"] * 501), encoding="utf-8")

    report = build_report(repo_root=tmp_path)

    oversized_paths = {metric.path for metric in report.oversized_files}
    assert ".ai/decisions.instructions.md" in oversized_paths
    assert "tools/browser-helper/server.js" in oversized_paths
    assert ".ai/qa/artifacts/coverage.md" not in oversized_paths


def test_audit_uses_tighter_tool_and_qa_entrypoint_budgets(
    tmp_path: Path,
) -> None:
    tool_entrypoint = tmp_path / "tools" / "camofox-browser" / "server.js"
    tool_entrypoint.parent.mkdir(parents=True)
    tool_entrypoint.write_text(
        "\n".join(["export const x = 1;"] * 451),
        encoding="utf-8",
    )
    qa_entrypoint = tmp_path / "scripts" / "qa" / "smoke_qa.py"
    qa_entrypoint.parent.mkdir(parents=True)
    qa_entrypoint.write_text("\n".join(["print('qa')"] * 651), encoding="utf-8")

    report = build_report(repo_root=tmp_path)

    metrics = {metric.path: metric for metric in report.oversized_files}
    assert metrics["tools/camofox-browser/server.js"].category == "tool-entrypoint"
    assert metrics["tools/camofox-browser/server.js"].threshold == 450
    assert metrics["scripts/qa/smoke_qa.py"].category == "qa-entrypoint"
    assert metrics["scripts/qa/smoke_qa.py"].threshold == 650
    assert should_fail_gate(report, fail_on_findings=True)
    assert not should_fail_gate(report, fail_on_findings=False)
