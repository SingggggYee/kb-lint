"""Tests for the orphans check."""

from __future__ import annotations

from kb_lint.checks.orphans import check
from kb_lint.models import Severity
from kb_lint.scanner import scan


def test_no_orphans_in_healthy_wiki(healthy_articles, default_config):
    issues = check(healthy_articles, default_config)
    assert len(issues) == 0


def test_detects_orphan(unhealthy_articles, default_config):
    issues = check(unhealthy_articles, default_config)
    orphan_files = {str(i.file) for i in issues}
    # orphan.md has no incoming links
    assert any("orphan.md" in f for f in orphan_files)


def test_orphans_are_warnings(unhealthy_articles, default_config):
    issues = check(unhealthy_articles, default_config)
    for issue in issues:
        assert issue.severity == Severity.WARNING


def test_index_not_flagged_as_orphan(unhealthy_articles, default_config):
    issues = check(unhealthy_articles, default_config)
    assert not any("_index.md" in str(i.file) for i in issues)


def test_linked_article_not_orphan(unhealthy_articles, default_config):
    """thin-article is linked from broken-links.md, so it's not an orphan."""
    issues = check(unhealthy_articles, default_config)
    assert not any("thin-article" in str(i.file) for i in issues)


def test_all_connected_no_orphans(tmp_path, default_config):
    """A wiki where every article links to every other has no orphans."""
    (tmp_path / "a.md").write_text("---\ntitle: A\n---\nSee [[b]]\n")
    (tmp_path / "b.md").write_text("---\ntitle: B\n---\nSee [[a]]\n")
    articles = scan(tmp_path, default_config)
    issues = check(articles, default_config)
    assert len(issues) == 0
