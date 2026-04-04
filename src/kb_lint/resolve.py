"""Shared wiki-link resolution logic."""

from __future__ import annotations

from kb_lint.models import Article


class ArticleIndex:
    """Pre-built lookup structure for resolving wiki-links to articles.

    Supports matching by:
    - Article stem (filename without extension), case-insensitive
    - Relative path without extension, case-insensitive
    - Path-style links where only the leaf matches a stem (e.g. "concepts/foo" -> "foo")
    - Links with a trailing .md suffix
    """

    def __init__(self, articles: list[Article]) -> None:
        self._stem_set: set[str] = set()
        self._rel_path_set: set[str] = set()
        self._stem_to_article: dict[str, Article] = {}
        self._stem_list: list[str] = []

        for a in articles:
            stem = a.path.stem.lower()
            self._stem_set.add(stem)
            self._stem_list.append(stem)
            self._stem_to_article[stem] = a

            rel_no_ext = str(a.relative_path.with_suffix("")).lower()
            self._rel_path_set.add(rel_no_ext)

    @property
    def stems(self) -> set[str]:
        return self._stem_set

    @property
    def stem_list(self) -> list[str]:
        return self._stem_list

    @property
    def stem_to_article(self) -> dict[str, Article]:
        return self._stem_to_article

    def resolve(self, link: str) -> Article | None:
        """Resolve a wiki-link text to an Article, or None if not found.

        Resolution order:
        1. Direct stem match (case-insensitive)
        2. Relative path match (without extension, case-insensitive)
        3. Path-style leaf match (e.g. "concepts/foo" matches stem "foo")
        4. Retry all above after stripping a trailing .md suffix
        """
        normalized = link.strip().lower()
        result = self._try_resolve(normalized)
        if result is not None:
            return result

        # Strip .md suffix and retry
        if normalized.endswith(".md"):
            return self._try_resolve(normalized[:-3])

        return None

    def _try_resolve(self, normalized: str) -> Article | None:
        # Direct stem match
        if normalized in self._stem_set:
            return self._stem_to_article.get(normalized)

        # Relative path match
        if normalized in self._rel_path_set:
            # Find the article by checking rel paths
            for a in self._stem_to_article.values():
                rel_no_ext = str(a.relative_path.with_suffix("")).lower()
                if rel_no_ext == normalized:
                    return a

        # Path-style leaf match: "concepts/foo" -> try stem "foo"
        parts = normalized.rsplit("/", 1)
        if len(parts) == 2:
            leaf = parts[1]
            if leaf in self._stem_set:
                return self._stem_to_article.get(leaf)

        return None


def resolve_link(link: str, articles: list[Article]) -> Article | None:
    """Convenience function: resolve a single wiki-link against a list of articles.

    For repeated lookups, prefer building an ArticleIndex once and calling
    its resolve() method.
    """
    index = ArticleIndex(articles)
    return index.resolve(link)


__all__ = ["ArticleIndex", "resolve_link"]
