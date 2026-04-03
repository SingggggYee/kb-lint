"""Check for missing or invalid YAML frontmatter fields."""

from __future__ import annotations

import re
from datetime import date

from kb_lint.config import Config
from kb_lint.models import Article, Issue, Severity

_DATE_PATTERNS = [
    re.compile(r"^\d{4}-\d{2}-\d{2}$"),  # YYYY-MM-DD
    re.compile(r"^\d{4}/\d{2}/\d{2}$"),  # YYYY/MM/DD
    re.compile(r"^\d{2}-\d{2}-\d{4}$"),  # MM-DD-YYYY
    re.compile(r"^\d{2}/\d{2}/\d{4}$"),  # MM/DD/YYYY
]


def _is_date_like(value: object) -> bool:
    """Check if a value looks like a date."""
    if isinstance(value, date):
        return True
    if isinstance(value, str):
        return any(p.match(value) for p in _DATE_PATTERNS)
    return False


def check(articles: list[Article], config: Config) -> list[Issue]:
    """Check frontmatter completeness and validity."""
    issues: list[Issue] = []

    for article in articles:
        fm = article.frontmatter

        # Skip _index.md from some checks
        is_index = article.path.name == "_index.md"

        # Check required fields
        for field_name in config.required_frontmatter:
            if field_name not in fm:
                issues.append(
                    Issue(
                        check="frontmatter",
                        severity=Severity.ERROR,
                        file=article.relative_path,
                        line=1,
                        message=f"Missing required frontmatter field: {field_name}",
                        suggestion=f"Add '{field_name}' to the frontmatter block",
                        fixable=True,
                    )
                )
            elif not fm[field_name]:
                issues.append(
                    Issue(
                        check="frontmatter",
                        severity=Severity.ERROR,
                        file=article.relative_path,
                        line=1,
                        message=f"Required frontmatter field '{field_name}' is empty",
                        suggestion=f"Set a value for '{field_name}'",
                        fixable=False,
                    )
                )

        # Check recommended fields (skip for index files)
        if not is_index:
            for field_name in config.recommended_frontmatter:
                if field_name not in fm:
                    issues.append(
                        Issue(
                            check="frontmatter",
                            severity=Severity.INFO,
                            file=article.relative_path,
                            line=1,
                            message=f"Missing recommended frontmatter field: {field_name}",
                            suggestion=f"Consider adding '{field_name}' to frontmatter",
                            fixable=True,
                        )
                    )

        # Type validations
        if "tags" in fm and fm["tags"] is not None:
            if not isinstance(fm["tags"], list):
                issues.append(
                    Issue(
                        check="frontmatter",
                        severity=Severity.WARNING,
                        file=article.relative_path,
                        line=1,
                        message="Frontmatter 'tags' should be a list",
                        suggestion="Use YAML list syntax: tags: [tag1, tag2]",
                        fixable=False,
                    )
                )

        if "confidence" in fm and fm["confidence"] is not None:
            conf = str(fm["confidence"]).lower()
            if conf not in config.allowed_confidence_levels:
                allowed = ", ".join(config.allowed_confidence_levels)
                issues.append(
                    Issue(
                        check="frontmatter",
                        severity=Severity.WARNING,
                        file=article.relative_path,
                        line=1,
                        message=f"Invalid confidence level: '{fm['confidence']}'",
                        suggestion=f"Use one of: {allowed}",
                        fixable=False,
                    )
                )

        # Date format validation
        for date_field in ("created", "updated", "date"):
            if date_field in fm and fm[date_field] is not None:
                if not _is_date_like(fm[date_field]):
                    issues.append(
                        Issue(
                            check="frontmatter",
                            severity=Severity.WARNING,
                            file=article.relative_path,
                            line=1,
                            message=(
                                f"Frontmatter '{date_field}' does not look"
                                f" like a valid date: {fm[date_field]}"
                            ),
                            suggestion="Use YYYY-MM-DD format",
                            fixable=False,
                        )
                    )

    return issues


__all__ = ["check"]
