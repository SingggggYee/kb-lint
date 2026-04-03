"""Data models for kb-lint."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Severity(Enum):
    """Issue severity levels."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Severity):
            return NotImplemented
        order = {Severity.INFO: 0, Severity.WARNING: 1, Severity.ERROR: 2}
        return order[self] < order[other]

    def __le__(self, other: object) -> bool:
        if not isinstance(other, Severity):
            return NotImplemented
        order = {Severity.INFO: 0, Severity.WARNING: 1, Severity.ERROR: 2}
        return order[self] <= order[other]

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, Severity):
            return NotImplemented
        order = {Severity.INFO: 0, Severity.WARNING: 1, Severity.ERROR: 2}
        return order[self] > order[other]

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, Severity):
            return NotImplemented
        order = {Severity.INFO: 0, Severity.WARNING: 1, Severity.ERROR: 2}
        return order[self] >= order[other]


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


@dataclass
class CheckResult:
    """Result from running a check."""

    check_name: str
    issues: list[Issue]
    articles_checked: int


__all__ = ["Severity", "Issue", "Article", "CheckResult"]
