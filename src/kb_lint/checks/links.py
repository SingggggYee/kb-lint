"""Check for broken wiki-links."""

from __future__ import annotations

import re
from difflib import get_close_matches

from kb_lint.config import Config
from kb_lint.models import Article, Issue, Severity
from kb_lint.resolve import ArticleIndex

_WIKI_LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def check(articles: list[Article], config: Config) -> list[Issue]:
    """Find broken wiki-links across all articles."""
    issues: list[Issue] = []
    idx = ArticleIndex(articles)

    for article in articles:
        for line_num, line in enumerate(article.raw.splitlines(), start=1):
            for match in _WIKI_LINK_RE.finditer(line):
                link_text = match.group(1)
                if idx.resolve(link_text) is None:
                    # Find closest match for suggestion
                    normalized = link_text.strip().lower()
                    close = get_close_matches(normalized, idx.stem_list, n=1, cutoff=0.6)
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
