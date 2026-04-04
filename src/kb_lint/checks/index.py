"""Check index accuracy — missing or extra entries."""

from __future__ import annotations

from kb_lint.config import Config
from kb_lint.models import Article, Issue, Severity
from kb_lint.resolve import ArticleIndex


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

    # Build index from non-index articles only
    idx = ArticleIndex(non_index_articles)

    # Extract all wiki-links from the index
    index_links: set[str] = set()
    for link in index_article.wiki_links:
        index_links.add(link.strip().lower())

    # Check for articles not listed in index
    for stem in sorted(idx.stems):
        # Check if any index link resolves to this article
        found = False
        for link in index_links:
            resolved = idx.resolve(link)
            if resolved is not None and resolved.path.stem.lower() == stem:
                found = True
                break
        if not found:
            article = idx.stem_to_article[stem]
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
        if idx.resolve(link) is None:
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
