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
from kb_lint.models import Article, Issue

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
    "links": "Broken [[wiki-links]] and optionally external URL checks",
    "frontmatter": "Missing or invalid YAML frontmatter fields",
    "orphans": "Articles with no incoming links",
    "structure": "Directory structure and naming conventions",
    "content": "Thin articles, template placeholders, duplicate titles",
    "index": "Index accuracy — missing or extra entries",
    "consistency": "Inconsistent tags, date formats, confidence levels",
}


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
    return all_issues


__all__ = ["REGISTRY", "CHECK_DESCRIPTIONS", "run_checks"]
