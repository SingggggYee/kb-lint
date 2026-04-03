"""Check for broken wiki-links and optionally external URLs."""

from __future__ import annotations

import re
from difflib import get_close_matches

from kb_lint.config import Config
from kb_lint.models import Article, Issue, Severity

_WIKI_LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def _resolve_wiki_link(link: str, article_stems: set[str], article_rel_paths: set[str]) -> bool:
    """Check if a wiki link resolves to a known article."""
    # Normalize: lowercase, strip whitespace
    normalized = link.strip().lower()

    # Try matching against stem (filename without extension)
    if normalized in article_stems:
        return True

    # Try matching against relative path without extension
    if normalized in article_rel_paths:
        return True

    # Try with .md suffix stripped from the link itself
    if normalized.endswith(".md"):
        without_md = normalized[:-3]
        if without_md in article_stems or without_md in article_rel_paths:
            return True

    return False


def check(articles: list[Article], config: Config) -> list[Issue]:
    """Find broken wiki-links across all articles."""
    issues: list[Issue] = []

    # Build lookup sets
    article_stems: set[str] = set()
    article_rel_paths: set[str] = set()
    stem_list: list[str] = []

    for a in articles:
        stem = a.path.stem.lower()
        article_stems.add(stem)
        stem_list.append(stem)

        rel_no_ext = str(a.relative_path.with_suffix("")).lower()
        article_rel_paths.add(rel_no_ext)

    for article in articles:
        for line_num, line in enumerate(article.raw.splitlines(), start=1):
            for match in _WIKI_LINK_RE.finditer(line):
                link_text = match.group(1)
                if not _resolve_wiki_link(link_text, article_stems, article_rel_paths):
                    # Find closest match for suggestion
                    normalized = link_text.strip().lower()
                    close = get_close_matches(normalized, stem_list, n=1, cutoff=0.6)
                    suggestion = f"Did you mean [[{close[0]}]]?" if close else None

                    issues.append(
                        Issue(
                            check="links",
                            severity=Severity.ERROR,
                            file=article.relative_path,
                            line=line_num,
                            message=f"Broken wiki-link: [[{link_text}]]",
                            suggestion=suggestion,
                            fixable=False,
                        )
                    )

    return issues


__all__ = ["check"]
