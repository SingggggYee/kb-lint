"""Registry of all available checks."""

from __future__ import annotations

from typing import Callable

from kb_lint.checks import (
    consistency,
    content,
    frontmatter,
    index,
    links,
    orphans,
    structure,
)
from kb_lint.config import Config
from kb_lint.models import Article, Issue, Severity

CheckFunc = Callable[[list[Article], Config], list[Issue]]

REGISTRY: dict[str, CheckFunc] = {
    "links": links.check,
    "frontmatter": frontmatter.check,
    "orphans": orphans.check,
    "structure": structure.check,
    "content": content.check,
    "index": index.check,
    "consistency": consistency.check,
}

CHECK_DESCRIPTIONS: dict[str, str] = {
    "links": "Broken [[wiki-links]]",
    "frontmatter": "Missing or invalid YAML frontmatter fields",
    "orphans": "Articles with no incoming links",
    "structure": "Directory structure and naming conventions",
    "content": "Thin articles, template placeholders, duplicate titles",
    "index": "Index accuracy — missing or extra entries",
    "consistency": "Inconsistent tags, date formats, confidence levels",
}


def _is_disabled(issue: Issue, articles: list[Article]) -> bool:
    """Check if an issue is suppressed by an inline disable directive."""
    _ALL = "__all__"

    # Find the article that this issue belongs to (issue.file may be absolute or relative)
    article = None
    for a in articles:
        if a.path == issue.file or a.relative_path == issue.file:
            article = a
            break
    if article is None:
        return False

    # Check file-level disables
    if _ALL in article.disabled_file_checks or issue.check in article.disabled_file_checks:
        return True

    # Check range disables (only if issue has a line number)
    if issue.line is not None:
        for check_name in (_ALL, issue.check):
            for start, end in article.disabled_checks.get(check_name, []):
                if start <= issue.line <= end:
                    return True

    return False


def run_checks(
    articles: list[Article],
    config: Config,
    selected_checks: list[str] | None = None,
) -> list[Issue]:
    """Run selected (or all configured) checks and return all issues."""
    checks_to_run = selected_checks or config.checks
    all_issues: list[Issue] = []
    for name in checks_to_run:
        func = REGISTRY.get(name)
        if func is not None:
            all_issues.extend(func(articles, config))
    # Apply per-check severity overrides
    for issue in all_issues:
        if issue.check in config.check_severity:
            issue.severity = Severity[config.check_severity[issue.check].upper()]

    # Filter out issues suppressed by inline disable comments
    all_issues = [i for i in all_issues if not _is_disabled(i, articles)]

    return all_issues


__all__ = ["REGISTRY", "CHECK_DESCRIPTIONS", "run_checks"]
