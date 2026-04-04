"""Check for inconsistencies across the knowledge base."""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date

from kb_lint.config import Config
from kb_lint.models import Article, Issue, Severity


def _detect_date_format(value: object) -> str | None:
    """Detect the date format used."""
    if isinstance(value, date):
        return "YYYY-MM-DD"
    if not isinstance(value, str):
        return None
    if re.match(r"^\d{4}-\d{2}-\d{2}$", value):
        return "YYYY-MM-DD"
    if re.match(r"^\d{4}/\d{2}/\d{2}$", value):
        return "YYYY/MM/DD"
    if re.match(r"^\d{2}-\d{2}-\d{4}$", value):
        return "MM-DD-YYYY"
    if re.match(r"^\d{2}/\d{2}/\d{4}$", value):
        return "MM/DD/YYYY"
    return None


def check(articles: list[Article], config: Config) -> list[Issue]:
    """Check for inconsistencies across articles."""
    issues: list[Issue] = []

    # --- Inconsistent tag casing ---
    # Group tags by their lowercase form
    tag_variants: dict[str, dict[str, list[Article]]] = defaultdict(lambda: defaultdict(list))
    for article in articles:
        tags = article.frontmatter.get("tags")
        if isinstance(tags, list):
            for tag in tags:
                if isinstance(tag, str):
                    tag_variants[tag.lower()][tag].append(article)

    for lower_tag, variants in tag_variants.items():
        if len(variants) > 1:
            variant_strs = []
            for v, arts in variants.items():
                files = ", ".join(str(a.relative_path) for a in arts)
                variant_strs.append(f"'{v}' in {files}")
            all_variants = "; ".join(variant_strs)
            # Report on the first article that uses a non-canonical form
            first_article = next(iter(next(iter(variants.values()))))
            issues.append(
                Issue(
                    check="consistency",
                    severity=Severity.WARNING,
                    file=first_article.relative_path,
                    line=None,
                    message=f"Inconsistent tag casing for '{lower_tag}': {all_variants}",
                    suggestion="Standardize tag casing across all articles",
                    fixable=False,
                )
            )

    # --- Inconsistent date formats ---
    date_formats: dict[str, list[Article]] = defaultdict(list)
    for article in articles:
        for field_name in ("created", "updated", "date"):
            value = article.frontmatter.get(field_name)
            if value is not None:
                fmt = _detect_date_format(value)
                if fmt:
                    date_formats[fmt].append(article)

    if len(date_formats) > 1:
        # Report on articles using the minority format
        most_common_fmt = max(date_formats, key=lambda f: len(date_formats[f]))
        for fmt, arts in date_formats.items():
            if fmt != most_common_fmt:
                for a in arts:
                    issues.append(
                        Issue(
                            check="consistency",
                            severity=Severity.WARNING,
                            file=a.relative_path,
                            line=None,
                            message=(
                            f"Inconsistent date format: uses {fmt}"
                            f" while most articles use {most_common_fmt}"
                        ),
                            suggestion=f"Standardize to {most_common_fmt} format",
                            fixable=False,
                        )
                    )

    # --- Confidence levels not in allowed set ---
    for article in articles:
        conf = article.frontmatter.get("confidence")
        if conf is not None:
            conf_str = str(conf).lower()
            if conf_str not in config.allowed_confidence_levels:
                allowed = ", ".join(config.allowed_confidence_levels)
                issues.append(
                    Issue(
                        check="consistency",
                        severity=Severity.WARNING,
                        file=article.relative_path,
                        line=None,
                        message=f"Invalid confidence level: '{conf}'",
                        suggestion=f"Use one of: {allowed}",
                        fixable=False,
                    )
                )

    # --- Inconsistent alias usage ---
    alias_variants: dict[str, dict[str, list[Article]]] = defaultdict(lambda: defaultdict(list))
    for article in articles:
        aliases = article.frontmatter.get("aliases")
        if isinstance(aliases, list):
            for alias in aliases:
                if isinstance(alias, str):
                    alias_variants[alias.lower()][alias].append(article)

    for lower_alias, variants in alias_variants.items():
        if len(variants) > 1:
            variant_strs = [f"'{v}'" for v in variants]
            first_article = next(iter(next(iter(variants.values()))))
            issues.append(
                Issue(
                    check="consistency",
                    severity=Severity.INFO,
                    file=first_article.relative_path,
                    line=None,
                    message=f"Inconsistent alias casing: {', '.join(variant_strs)}",
                    suggestion="Standardize alias casing",
                    fixable=False,
                )
            )

    return issues


__all__ = ["check"]
