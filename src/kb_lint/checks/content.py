"""Check content quality: thin articles, placeholders, duplicates, empty sections."""

from __future__ import annotations

import re

from kb_lint.config import Config
from kb_lint.models import Article, Issue, Severity

_PLACEHOLDER_RE = re.compile(r"\{\{[A-Z_]+\}\}")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


def check(articles: list[Article], config: Config) -> list[Issue]:
    """Check content quality across all articles."""
    issues: list[Issue] = []
    titles_seen: dict[str, Article] = {}

    for article in articles:
        # Skip _index.md from thin-article checks
        is_index = article.path.name == "_index.md"

        # Pre-compute frontmatter line count for this article
        fm_lines = 0
        if article.raw.startswith("---"):
            end = article.raw.find("---", 3)
            if end != -1:
                fm_lines = article.raw[:end + 3].count("\n") + 1

        # --- Thin articles ---
        if not is_index and article.word_count < config.min_article_words:
            issues.append(
                Issue(
                    check="content",
                    severity=Severity.WARNING,
                    file=article.relative_path,
                    line=None,
                    message=(
                        f"Thin article: only {article.word_count} words"
                        f" (minimum: {config.min_article_words})"
                    ),
                    suggestion="Expand this article with more detail",
                    fixable=False,
                )
            )

        # --- Template placeholders ---
        for line_num, line in enumerate(article.content.splitlines(), start=1):
            for match in _PLACEHOLDER_RE.finditer(line):
                issues.append(
                    Issue(
                        check="content",
                        severity=Severity.ERROR,
                        file=article.relative_path,
                        line=line_num + fm_lines,
                        message=f"Template placeholder: {match.group()}",
                        suggestion="Replace the placeholder with actual content",
                        fixable=False,
                    )
                )

        # --- Duplicate titles ---
        title_lower = article.title.lower().strip()
        if title_lower:
            if title_lower in titles_seen:
                other = titles_seen[title_lower]
                issues.append(
                    Issue(
                        check="content",
                        severity=Severity.WARNING,
                        file=article.relative_path,
                        line=None,
                        message=(
                            f"Duplicate title: '{article.title}'"
                            f", also in {other.relative_path}"
                        ),
                        suggestion="Give each article a unique title",
                        fixable=False,
                    )
                )
            else:
                titles_seen[title_lower] = article

        # --- Empty sections ---
        headings = list(_HEADING_RE.finditer(article.content))
        for i, heading_match in enumerate(headings):
            # Check if the next heading immediately follows with no content between
            start_pos = heading_match.end()
            if i + 1 < len(headings):
                end_pos = headings[i + 1].start()
            else:
                end_pos = len(article.content)

            between = article.content[start_pos:end_pos].strip()
            if not between:
                # Calculate line number
                line_num = article.content[: heading_match.start()].count("\n") + 1
                issues.append(
                    Issue(
                        check="content",
                        severity=Severity.WARNING,
                        file=article.relative_path,
                        line=line_num + fm_lines,
                        message=f"Empty section: '{heading_match.group(2)}'",
                        suggestion="Add content under this heading or remove it",
                        fixable=False,
                    )
                )

    return issues


__all__ = ["check"]
