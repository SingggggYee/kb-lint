"""Check for orphan articles with no incoming links."""

from __future__ import annotations

from kb_lint.config import Config
from kb_lint.models import Article, Issue, Severity
from kb_lint.resolve import ArticleIndex


def check(articles: list[Article], config: Config) -> list[Issue]:
    """Find articles that have no incoming wiki-links from other articles."""
    issues: list[Issue] = []
    idx = ArticleIndex(articles)

    # Build incoming link counts
    incoming: dict[str, int] = {stem: 0 for stem in idx.stems}

    for article in articles:
        for link in article.wiki_links:
            resolved = idx.resolve(link)
            if resolved is not None:
                target_stem = resolved.path.stem.lower()
                incoming[target_stem] = incoming.get(target_stem, 0) + 1

    # Report orphans
    for stem, count in incoming.items():
        article = idx.stem_to_article[stem]

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
                    message="Orphan page: no incoming links",
                    suggestion="Add a [[wiki-link]] to this page from a related article or index",
                    fixable=False,
                )
            )

    return issues


__all__ = ["check"]
