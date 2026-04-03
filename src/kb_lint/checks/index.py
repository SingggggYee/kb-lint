"""Check index accuracy — missing or extra entries."""

from __future__ import annotations

import re

from kb_lint.config import Config
from kb_lint.models import Article, Issue, Severity

_WIKI_LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def check(articles: list[Article], config: Config) -> list[Issue]:
    """Check that _index.md accurately lists all articles."""
    issues: list[Issue] = []

    # Find the index article
    index_article: Article | None = None
    non_index_articles: list[Article] = []

    for article in articles:
        if article.path.name == "_index.md":
            index_article = article
        else:
            non_index_articles.append(article)

    if index_article is None:
        # No index file — only report if there are articles to index
        if non_index_articles:
            issues.append(
                Issue(
                    check="index",
                    severity=Severity.WARNING,
                    file=non_index_articles[0].relative_path.parent / "_index.md",
                    line=None,
                    message="No _index.md found in the knowledge base",
                    suggestion="Create an _index.md listing all articles",
                    fixable=True,
                )
            )
        return issues

    # Extract all wiki-links from the index
    index_links: set[str] = set()
    for link in index_article.wiki_links:
        index_links.add(link.strip().lower())

    # Build set of article stems
    article_stems: set[str] = set()
    stem_to_article: dict[str, Article] = {}
    for a in non_index_articles:
        stem = a.path.stem.lower()
        article_stems.add(stem)
        stem_to_article[stem] = a

    # Check for articles not listed in index
    for stem in sorted(article_stems):
        if stem not in index_links:
            # Also check if any index link resolves to this stem via path
            found = False
            for link in index_links:
                if link.endswith("/" + stem) or link == stem:
                    found = True
                    break
            if not found:
                article = stem_to_article[stem]
                issues.append(
                    Issue(
                        check="index",
                        severity=Severity.WARNING,
                        file=index_article.relative_path,
                        line=None,
                        message=f"Article '{article.relative_path}' is not listed in the index",
                        suggestion=f"Add [[{stem}]] to _index.md",
                        fixable=True,
                    )
                )

    # Check for index entries pointing to non-existent articles
    for link in sorted(index_links):
        normalized = link.strip().lower()
        # Check against stems
        if normalized in article_stems:
            continue
        # Check path-style links
        parts = normalized.rsplit("/", 1)
        if len(parts) == 2 and parts[1] in article_stems:
            continue
        issues.append(
            Issue(
                check="index",
                severity=Severity.ERROR,
                file=index_article.relative_path,
                line=None,
                message=f"Index entry [[{link}]] points to a non-existent article",
                suggestion="Remove this entry or create the missing article",
                fixable=False,
            )
        )

    # Check for duplicate entries in index
    link_counts: dict[str, int] = {}
    for link in index_article.wiki_links:
        key = link.strip().lower()
        link_counts[key] = link_counts.get(key, 0) + 1

    for link, count in link_counts.items():
        if count > 1:
            issues.append(
                Issue(
                    check="index",
                    severity=Severity.INFO,
                    file=index_article.relative_path,
                    line=None,
                    message=f"Duplicate index entry: [[{link}]] appears {count} times",
                    suggestion="Remove duplicate entries",
                    fixable=True,
                )
            )

    return issues


__all__ = ["check"]
