"""Check for orphan articles with no incoming links."""

from __future__ import annotations

from kb_lint.config import Config
from kb_lint.models import Article, Issue, Severity


def check(articles: list[Article], config: Config) -> list[Issue]:
    """Find articles that have no incoming wiki-links from other articles."""
    issues: list[Issue] = []

    # Build a set of all article stems (lowercase)
    stem_to_article: dict[str, Article] = {}
    for a in articles:
        stem_to_article[a.path.stem.lower()] = a

    # Build incoming link counts
    incoming: dict[str, int] = {stem: 0 for stem in stem_to_article}

    for article in articles:
        for link in article.wiki_links:
            target = link.strip().lower()
            # Try direct stem match
            if target in incoming:
                incoming[target] += 1
            else:
                # Try matching link as path (e.g., "concepts/foo")
                parts = target.rsplit("/", 1)
                if len(parts) == 2:
                    leaf = parts[1]
                    if leaf in incoming:
                        incoming[leaf] += 1

    # Report orphans
    for stem, count in incoming.items():
        article = stem_to_article[stem]

        # Skip index files — they are roots, not orphans
        if article.path.name == "_index.md":
            continue

        if count == 0:
            issues.append(
                Issue(
                    check="orphans",
                    severity=Severity.WARNING,
                    file=article.relative_path,
                    line=None,
                    message="Orphan article: no other article links to this page",
                    suggestion="Add a [[wiki-link]] to this article from a related page or index",
                    fixable=False,
                )
            )

    return issues


__all__ = ["check"]
