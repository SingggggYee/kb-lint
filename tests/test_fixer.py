"""Tests for the auto-fixer."""

from __future__ import annotations

from pathlib import Path

import frontmatter

from kb_lint.config import Config
from kb_lint.fixer import (
    apply_fixes,
    fix_duplicate_index_entries,
    fix_filename_casing,
    fix_missing_frontmatter,
)
from kb_lint.models import Article
from kb_lint.scanner import scan


def _make_article(path: Path, text: str) -> Article:
    """Write a file and scan it into an Article."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    config = Config()
    articles = scan(path.parent, config)
    for a in articles:
        if a.path == path:
            return a
    raise RuntimeError(f"Could not find article at {path}")


def test_fix_missing_frontmatter(tmp_path):
    article = _make_article(
        tmp_path / "test.md",
        "# No frontmatter\n\nJust content here.\n",
    )
    config = Config()
    changed, desc = fix_missing_frontmatter(article, config)
    assert changed
    assert "title" in desc

    # Verify backup was created
    bak = tmp_path / "test.md.bak"
    assert bak.exists()

    # Verify frontmatter was added
    post = frontmatter.load(str(tmp_path / "test.md"))
    assert "title" in post.metadata


def test_fix_missing_frontmatter_adds_recommended(tmp_path):
    article = _make_article(
        tmp_path / "test.md",
        "---\ntitle: Test\n---\n\nContent here.\n",
    )
    config = Config()
    changed, desc = fix_missing_frontmatter(article, config)
    assert changed
    # Should have added recommended fields
    post = frontmatter.load(str(tmp_path / "test.md"))
    assert "tags" in post.metadata
    assert "confidence" in post.metadata


def test_fix_filename_casing(tmp_path):
    path = tmp_path / "Bad Name.md"
    article = _make_article(path, "---\ntitle: Bad\n---\nContent.\n")
    changed, desc = fix_filename_casing(article)
    assert changed
    assert "bad-name.md" in desc

    # Old file should be gone (renamed)
    assert not path.exists()
    # New file should exist
    assert (tmp_path / "bad-name.md").exists()
    # Backup should exist
    assert (tmp_path / "Bad Name.md.bak").exists()


def test_fix_filename_already_correct(tmp_path):
    path = tmp_path / "good-name.md"
    article = _make_article(path, "---\ntitle: Good\n---\nContent.\n")
    changed, desc = fix_filename_casing(article)
    assert not changed


def test_fix_duplicate_index_entries(tmp_path):
    path = tmp_path / "_index.md"
    path.write_text(
        "---\ntitle: Index\n---\n\n- [[a]]\n- [[b]]\n- [[a]]\n- [[c]]\n- [[b]]\n",
        encoding="utf-8",
    )
    config = Config()
    articles = scan(tmp_path, config)
    index_article = next(a for a in articles if a.path.name == "_index.md")

    changed, desc = fix_duplicate_index_entries(index_article)
    assert changed
    assert "2" in desc  # removed 2 duplicates

    # Verify backup
    assert (tmp_path / "_index.md.bak").exists()

    # Verify content
    content = path.read_text()
    assert content.count("[[a]]") == 1
    assert content.count("[[b]]") == 1
    assert content.count("[[c]]") == 1


def test_apply_fixes_integration(unhealthy_wiki, default_config):
    """Integration test: apply_fixes on the unhealthy wiki."""
    articles = scan(unhealthy_wiki, default_config)
    from kb_lint.checks import run_checks

    issues = run_checks(articles, default_config)
    fixable = [i for i in issues if i.fixable]
    assert len(fixable) > 0

    fixes = apply_fixes(issues, articles, unhealthy_wiki, default_config)
    # Some fixes should have been applied
    assert len(fixes) > 0

    # Verify at least one .bak file was created
    bak_files = list(unhealthy_wiki.rglob("*.bak"))
    assert len(bak_files) > 0
