"""Data models for kb-lint."""

from __future__ import annotations

import functools
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


@functools.total_ordering
class Severity(Enum):
    """Issue severity levels."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Severity):
            return NotImplemented
        return self.value == other.value

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Severity):
            return NotImplemented
        order = {Severity.INFO: 0, Severity.WARNING: 1, Severity.ERROR: 2}
        return order[self] < order[other]

    def __hash__(self) -> int:
        return hash(self.value)


@dataclass
class Issue:
    """A single lint issue found in the knowledge base."""

    check: str
    severity: Severity
    file: Path
    line: int | None
    message: str
    suggestion: str | None = None
    fixable: bool = False


@dataclass
class Article:
    """A parsed markdown article from the knowledge base."""

    path: Path
    relative_path: Path
    frontmatter: dict
    content: str
    raw: str
    title: str
    wiki_links: list[str] = field(default_factory=list)
    word_count: int = 0
    disabled_checks: dict[str, list[tuple[int, int]]] = field(default_factory=dict)
    disabled_file_checks: set[str] = field(default_factory=set)


@dataclass
class CheckResult:
    """Result from running a check."""

    check_name: str
    issues: list[Issue]
    articles_checked: int


__all__ = ["Severity", "Issue", "Article", "CheckResult"]
