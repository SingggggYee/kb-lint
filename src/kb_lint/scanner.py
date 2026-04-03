"""Scan a directory and build an article inventory."""

from __future__ import annotations

import re
from pathlib import Path

import frontmatter
import pathspec

from kb_lint.config import Config
from kb_lint.models import Article

_WIKI_LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def _is_binary(path: Path) -> bool:
    """Heuristic check for binary files."""
    try:
        with open(path, "rb") as f:
            chunk = f.read(8192)
        return b"\x00" in chunk
    except OSError:
        return True


def _build_ignore_spec(wiki_path: Path, config: Config) -> pathspec.PathSpec:
    """Build a pathspec from config ignore patterns and .gitignore."""
    patterns = list(config.ignore_patterns)

    gitignore = wiki_path / ".gitignore"
    if gitignore.is_file():
        with open(gitignore) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line)

    return pathspec.PathSpec.from_lines("gitignore", patterns)


def scan(wiki_path: Path, config: Config) -> list[Article]:
    """Recursively scan wiki_path for markdown files and parse them into Articles."""
    wiki_path = wiki_path.resolve()
    if not wiki_path.is_dir():
        return []

    ignore_spec = _build_ignore_spec(wiki_path, config)
    articles: list[Article] = []

    for md_file in sorted(wiki_path.rglob("*.md")):
        rel = md_file.relative_to(wiki_path)

        # Skip ignored paths
        if ignore_spec.match_file(str(rel)):
            continue

        # Skip binary files that happen to have .md extension
        if _is_binary(md_file):
            continue

        try:
            raw_text = md_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        # Parse frontmatter
        try:
            post = frontmatter.loads(raw_text)
            fm = dict(post.metadata)
            content = post.content
        except Exception:
            fm = {}
            content = raw_text

        # Extract wiki links
        wiki_links = _WIKI_LINK_RE.findall(content)

        # Compute word count (content only, no frontmatter)
        words = content.split()
        word_count = len(words)

        # Derive title
        title = fm.get("title", "")
        if not title:
            # Fall back to first H1 in content
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith("# "):
                    title = stripped[2:].strip()
                    break
            if not title:
                title = md_file.stem.replace("-", " ").title()

        articles.append(
            Article(
                path=md_file,
                relative_path=rel,
                frontmatter=fm,
                content=content,
                raw=raw_text,
                title=title,
                wiki_links=wiki_links,
                word_count=word_count,
            )
        )

    return articles


__all__ = ["scan"]
