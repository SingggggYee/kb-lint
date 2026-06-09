"""Scan a directory and build an article inventory."""

from __future__ import annotations

import re
from pathlib import Path

import frontmatter
import pathspec
import yaml

from kb_lint.config import Config
from kb_lint.models import Article

_WIKI_LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")

# Disable-comment patterns
_DISABLE_FILE_RE = re.compile(r"<!--\s*kb-lint-disable-file(?:\s+(\S+))?\s*-->")
_DISABLE_NEXT_LINE_RE = re.compile(r"<!--\s*kb-lint-disable-next-line(?:\s+(\S+))?\s*-->")
_DISABLE_RE = re.compile(r"<!--\s*kb-lint-disable(?:\s+(\S+))?\s*-->")
_ENABLE_RE = re.compile(r"<!--\s*kb-lint-enable(?:\s+(\S+))?\s*-->")


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


def _parse_disable_directives(
    raw: str,
) -> tuple[dict[str, list[tuple[int, int]]], set[str]]:
    """Parse kb-lint disable/enable comments from raw markdown text.

    Returns (disabled_checks, disabled_file_checks).
    """
    _ALL = "__all__"
    disabled_checks: dict[str, list[tuple[int, int]]] = {}
    disabled_file_checks: set[str] = set()

    # Track open ranges: check_name -> start_line
    open_ranges: dict[str, int] = {}

    lines = raw.splitlines()
    total_lines = len(lines)

    for line_num, line in enumerate(lines, start=1):
        # Check disable-file first (most specific prefix)
        m = _DISABLE_FILE_RE.search(line)
        if m:
            check_name = m.group(1) or _ALL
            disabled_file_checks.add(check_name)
            continue

        # Check disable-next-line
        m = _DISABLE_NEXT_LINE_RE.search(line)
        if m:
            check_name = m.group(1) or _ALL
            next_line = line_num + 1
            disabled_checks.setdefault(check_name, []).append((next_line, next_line))
            continue

        # Check enable (must test before disable since disable pattern also matches enable text)
        m = _ENABLE_RE.search(line)
        if m and not _DISABLE_NEXT_LINE_RE.search(line) and not _DISABLE_FILE_RE.search(line):
            check_name = m.group(1) or _ALL
            if check_name in open_ranges:
                start = open_ranges.pop(check_name)
                disabled_checks.setdefault(check_name, []).append((start, line_num))
            continue

        # Check disable (range start)
        m = _DISABLE_RE.search(line)
        if (
            m
            and not _DISABLE_NEXT_LINE_RE.search(line)
            and not _DISABLE_FILE_RE.search(line)
            and not _ENABLE_RE.search(line)
        ):
            check_name = m.group(1) or _ALL
            open_ranges[check_name] = line_num

    # Close any unclosed ranges at end of file
    for check_name, start in open_ranges.items():
        disabled_checks.setdefault(check_name, []).append((start, total_lines))

    return disabled_checks, disabled_file_checks


def _parse_article(md_file: Path, rel: Path) -> Article | None:
    """Parse a single markdown file into an Article, or return None on failure."""
    if _is_binary(md_file):
        return None

    try:
        raw_text = md_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    # Parse frontmatter
    try:
        post = frontmatter.loads(raw_text)
        fm = dict(post.metadata)
        content = post.content
    except yaml.YAMLError:
        fm = {}
        content = raw_text

    # Extract wiki links
    wiki_links = _WIKI_LINK_RE.findall(content)

    # Compute word count (content only, no frontmatter)
    words = content.split()
    word_count = len(words)

    # Derive title
    title = str(fm.get("title", "") or "")
    if not title:
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                title = stripped[2:].strip()
                break
        if not title:
            title = md_file.stem.replace("-", " ").title()

    # Parse inline disable directives
    disabled_checks, disabled_file_checks = _parse_disable_directives(raw_text)

    return Article(
        path=md_file,
        relative_path=rel,
        frontmatter=fm,
        content=content,
        raw=raw_text,
        title=title,
        wiki_links=wiki_links,
        word_count=word_count,
        disabled_checks=disabled_checks,
        disabled_file_checks=disabled_file_checks,
    )


def scan(
    wiki_path: Path,
    config: Config,
    changed_files: set[Path] | None = None,
    previous_articles: list[Article] | None = None,
) -> list[Article]:
    """Recursively scan wiki_path for markdown files and parse them into Articles.

    When *changed_files* and *previous_articles* are provided, only files in
    *changed_files* are re-parsed from disk.  Unchanged files reuse their
    cached Article objects from *previous_articles*, which avoids redundant I/O
    and parsing for large knowledge bases.
    """
    wiki_path = wiki_path.resolve()
    if not wiki_path.is_dir():
        return []

    ignore_spec = _build_ignore_spec(wiki_path, config)

    # Build a lookup of cached articles by resolved path for fast reuse
    cached: dict[Path, Article] = {}
    if changed_files is not None and previous_articles is not None:
        cached = {a.path.resolve(): a for a in previous_articles}

    articles: list[Article] = []

    for md_file in sorted(wiki_path.rglob("*.md")):
        rel = md_file.relative_to(wiki_path)

        # Skip ignored paths
        if ignore_spec.match_file(str(rel)):
            continue

        resolved = md_file.resolve()

        # Reuse cached article if the file was not modified
        if cached and changed_files is not None and resolved not in changed_files:
            prev = cached.get(resolved)
            if prev is not None:
                articles.append(prev)
                continue

        article = _parse_article(md_file, rel)
        if article is not None:
            articles.append(article)

    return articles


__all__ = ["scan"]
