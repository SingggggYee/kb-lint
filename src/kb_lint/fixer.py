"""Auto-fix simple issues in the knowledge base."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import frontmatter

from kb_lint.config import Config
from kb_lint.models import Article, Issue


def _backup(path: Path) -> Path:
    """Create a .bak backup of a file, returning the backup path."""
    bak = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, bak)
    return bak


def fix_missing_frontmatter(article: Article, config: Config) -> tuple[bool, str]:
    """Add missing required/recommended frontmatter fields with defaults."""
    post = frontmatter.loads(article.raw)
    changed = False
    added_fields: list[str] = []

    for field_name in config.required_frontmatter:
        if field_name not in post.metadata:
            if field_name == "title":
                post.metadata[field_name] = article.title
            else:
                post.metadata[field_name] = ""
            changed = True
            added_fields.append(field_name)

    for field_name in config.recommended_frontmatter:
        if field_name not in post.metadata:
            if field_name == "tags":
                post.metadata[field_name] = []
            elif field_name == "sources":
                post.metadata[field_name] = []
            elif field_name == "related":
                post.metadata[field_name] = []
            elif field_name == "confidence":
                post.metadata[field_name] = "medium"
            elif field_name == "created":
                post.metadata[field_name] = ""
            else:
                post.metadata[field_name] = ""
            changed = True
            added_fields.append(field_name)

    if changed:
        _backup(article.path)
        article.path.write_text(frontmatter.dumps(post), encoding="utf-8")

    desc = f"Added fields: {', '.join(added_fields)}" if added_fields else "No changes"
    return changed, desc


def fix_filename_casing(article: Article) -> tuple[bool, str]:
    """Rename files with spaces or non-kebab-case names."""
    stem = article.path.stem
    new_stem = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")
    new_name = new_stem + ".md"

    if new_name == article.path.name:
        return False, "Already correct"

    new_path = article.path.parent / new_name
    if new_path.exists():
        return False, f"Cannot rename: '{new_name}' already exists"

    _backup(article.path)
    article.path.rename(new_path)
    return True, f"Renamed '{article.path.name}' -> '{new_name}'"


def fix_index_missing_articles(
    index_article: Article,
    missing_stems: list[str],
) -> tuple[bool, str]:
    """Append missing articles to the index."""
    if not missing_stems:
        return False, "No missing articles"

    _backup(index_article.path)

    content = index_article.path.read_text(encoding="utf-8")
    additions = "\n".join(f"- [[{stem}]]" for stem in sorted(missing_stems))
    updated = content.rstrip() + "\n\n" + additions + "\n"
    index_article.path.write_text(updated, encoding="utf-8")

    return True, f"Added {len(missing_stems)} entries to index"


def fix_duplicate_index_entries(index_article: Article) -> tuple[bool, str]:
    """Remove duplicate wiki-link entries from _index.md."""
    lines = index_article.raw.splitlines()
    seen_links: set[str] = set()
    new_lines: list[str] = []
    removed = 0

    wiki_link_re = re.compile(r"\[\[([^\]]+)\]\]")

    for line in lines:
        match = wiki_link_re.search(line)
        if match:
            link = match.group(1).strip().lower()
            if link in seen_links:
                removed += 1
                continue
            seen_links.add(link)
        new_lines.append(line)

    if removed > 0:
        _backup(index_article.path)
        index_article.path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        return True, f"Removed {removed} duplicate entries"

    return False, "No duplicates found"


def apply_fixes(
    issues: list[Issue],
    articles: list[Article],
    wiki_path: Path,
    config: Config,
) -> list[str]:
    """Apply auto-fixes for all fixable issues. Returns list of fix descriptions."""
    fixes: list[str] = []

    # Group issues by type for batch operations
    frontmatter_files: set[Path] = set()
    filename_files: set[Path] = set()
    index_missing: list[str] = []
    index_duplicates = False

    for issue in issues:
        if not issue.fixable:
            continue
        if issue.check == "frontmatter":
            frontmatter_files.add(issue.file)
        elif issue.check == "structure" and "spaces" in issue.message.lower() or (
            issue.check == "structure" and "kebab" in issue.message.lower()
        ):
            filename_files.add(issue.file)
        elif issue.check == "index" and "not listed" in issue.message:
            # Extract stem from the suggestion
            match = re.search(r"\[\[(\w[\w-]*)\]\]", issue.suggestion or "")
            if match:
                index_missing.append(match.group(1))
        elif issue.check == "index" and "Duplicate" in issue.message:
            index_duplicates = True

    # Build lookup from relative path to article
    art_by_rel: dict[Path, Article] = {a.relative_path: a for a in articles}

    # Fix frontmatter
    for rel_path in frontmatter_files:
        article = art_by_rel.get(rel_path)
        if article:
            changed, desc = fix_missing_frontmatter(article, config)
            if changed:
                fixes.append(f"{rel_path}: {desc}")

    # Fix filenames
    for rel_path in filename_files:
        article = art_by_rel.get(rel_path)
        if article:
            changed, desc = fix_filename_casing(article)
            if changed:
                fixes.append(f"{rel_path}: {desc}")

    # Fix index
    index_article = next((a for a in articles if a.path.name == "_index.md"), None)
    if index_article:
        if index_missing:
            changed, desc = fix_index_missing_articles(index_article, index_missing)
            if changed:
                fixes.append(f"_index.md: {desc}")

        if index_duplicates:
            changed, desc = fix_duplicate_index_entries(index_article)
            if changed:
                fixes.append(f"_index.md: {desc}")

    return fixes


__all__ = ["apply_fixes"]
