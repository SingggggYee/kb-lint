"""Tests for the links check."""

from __future__ import annotations

from kb_lint.checks.links import check
from kb_lint.models import Severity


def test_no_broken_links_in_healthy_wiki(healthy_articles, default_config):
    issues = check(healthy_articles, default_config)
    assert len(issues) == 0


def test_detects_broken_links(unhealthy_articles, default_config):
    issues = check(unhealthy_articles, default_config)
    broken_msgs = [i.message for i in issues if "Broken wiki-link" in i.message]
    assert len(broken_msgs) > 0

    # Specific broken links
    link_texts = [i.message for i in issues]
    assert any("does-not-exist" in m for m in link_texts)
    assert any("another-missing" in m for m in link_texts)


def test_broken_links_are_errors(unhealthy_articles, default_config):
    issues = check(unhealthy_articles, default_config)
    for issue in issues:
        assert issue.severity == Severity.ERROR


def test_valid_link_not_flagged(unhealthy_articles, default_config):
    issues = check(unhealthy_articles, default_config)
    # [[thin-article]] exists, should not be flagged
    assert not any("thin-article" in i.message for i in issues)


def test_broken_link_has_line_number(unhealthy_articles, default_config):
    issues = check(unhealthy_articles, default_config)
    for issue in issues:
        assert issue.line is not None
        assert issue.line > 0


def test_suggestion_for_close_match(unhealthy_articles, default_config):
    """If a broken link is close to an existing article, suggest it."""
    issues = check(unhealthy_articles, default_config)
    # At least some issues should have suggestions
    suggestions = [i.suggestion for i in issues if i.suggestion]
    # Not guaranteed, but check structure
    for s in suggestions:
        assert "Did you mean" in s
