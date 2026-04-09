"""Check directory structure and naming conventions."""

from __future__ import annotations

import re

from kb_lint.config import Config
from kb_lint.models import Article, Issue, Severity

_KEBAB_CASE_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def _is_kebab_case(name: str) -> bool:
    """Check if a filename stem is kebab-case."""
    # Allow _index as a special case
    if name == "_index":
        return True
    return bool(_KEBAB_CASE_RE.match(name))


def check(articles: list[Article], config: Config) -> list[Issue]:
    """Check naming conventions and directory structure."""
    issues: list[Issue] = []
    seen_stems: dict[str, Article] = {}

    for article in articles:
        stem = article.path.stem
        filename = article.path.name

        # Check for spaces in filename
        if " " in filename:
            issues.append(
                Issue(
                    check="structure",
                    severity=Severity.ERROR,
                    file=article.relative_path,
                    line=None,
                    message=f"Filename contains spaces: '{filename}'",
                    suggestion=f"Rename to '{filename.replace(' ', '-').lower()}'",
                    fixable=True,
                )
            )

        # Check kebab-case
        elif not _is_kebab_case(stem):
            kebab = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")
            issues.append(
                Issue(
                    check="structure",
                    severity=Severity.WARNING,
                    file=article.relative_path,
                    line=None,
                    message=f"Filename is not kebab-case: '{stem}'",
                    suggestion=f"Rename to '{kebab}.md'",
                    fixable=True,
                )
            )

        # Check for duplicate stems across directories
        lower_stem = stem.lower()
        if lower_stem in seen_stems:
            other = seen_stems[lower_stem]
            issues.append(
                Issue(
                    check="structure",
                    severity=Severity.WARNING,
                    file=article.relative_path,
                    line=None,
                    message=f"Duplicate filename '{stem}' also exists at {other.relative_path}",
                    suggestion="Rename one of the files to avoid ambiguous wiki-links",
                    fixable=False,
                )
            )
        else:
            seen_stems[lower_stem] = article

        # Check directory is recognized (only for files in subdirectories)
        parts = article.relative_path.parts
        if len(parts) > 1:
            top_dir = parts[0]
            if top_dir not in config.recognized_directories and not top_dir.startswith("_"):
                recognized = ", ".join(config.recognized_directories)
                issues.append(
                    Issue(
                        check="structure",
                        severity=Severity.INFO,
                        file=article.relative_path,
                        line=None,
                        message=f"Unrecognized directory: '{top_dir}'",
                        suggestion=f"Consider using one of: {recognized}",
                        fixable=False,
                    )
                )

    return issues


__all__ = ["check"]
