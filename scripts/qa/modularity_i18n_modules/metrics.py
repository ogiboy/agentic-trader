from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FileMetric:
    path: str
    lines: int
    threshold: int
    category: str

    def as_json(self) -> dict[str, object]:
        return {
            "path": self.path,
            "lines": self.lines,
            "threshold": self.threshold,
            "category": self.category,
        }


@dataclass(frozen=True)
class FunctionMetric:
    path: str
    name: str
    line: int
    lines: int

    def as_json(self) -> dict[str, object]:
        return {
            "path": self.path,
            "name": self.name,
            "line": self.line,
            "lines": self.lines,
        }


@dataclass(frozen=True)
class HelperMetric:
    name: str
    paths: tuple[str, ...]

    def as_json(self) -> dict[str, object]:
        return {"name": self.name, "paths": list(self.paths), "count": len(self.paths)}


@dataclass(frozen=True)
class CopyCandidate:
    path: str
    line: int
    excerpt: str

    def as_json(self) -> dict[str, object]:
        return {"path": self.path, "line": self.line, "excerpt": self.excerpt}


@dataclass(frozen=True)
class LocaleParity:
    english_only: tuple[str, ...]
    turkish_only: tuple[str, ...]

    def as_json(self) -> dict[str, object]:
        return {
            "english_only": list(self.english_only),
            "turkish_only": list(self.turkish_only),
        }


@dataclass(frozen=True)
class AuditReport:
    oversized_files: tuple[FileMetric, ...]
    long_functions: tuple[FunctionMetric, ...]
    repeated_helpers: tuple[HelperMetric, ...]
    copy_candidates: tuple[CopyCandidate, ...]
    docs_locale_parity: LocaleParity
    scanned_files: int

    def as_json(self) -> dict[str, object]:
        return {
            "scanned_files": self.scanned_files,
            "oversized_files": [metric.as_json() for metric in self.oversized_files],
            "long_functions": [metric.as_json() for metric in self.long_functions],
            "repeated_helpers": [metric.as_json() for metric in self.repeated_helpers],
            "copy_candidates": [
                candidate.as_json() for candidate in self.copy_candidates
            ],
            "docs_locale_parity": self.docs_locale_parity.as_json(),
        }
