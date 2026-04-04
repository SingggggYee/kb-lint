"""Tests for the consistency check."""

from __future__ import annotations

from pathlib import Path

from kb_lint.checks.consistency import check
from kb_lint.config import Config
from kb_lint.models import Article, Severity


def _make_article(
    rel: str,
    frontmatter: dict,
    content: str = "Enough words " * 50,
) -> Article:
    return Article(
        path=Path("/wiki") / rel,
        relative_path=Path(rel),
        frontmatter=frontmatter,
        content=content,
        raw="---\n---\n" + content,
        title=frontmatter.get("title", "Test"),
        wiki_links=[],
        word_count=len(content.split()),
    )


def test_tag_casing_inconsistency():
    """Detect when the same tag appears with different casing across articles."""
    articles = [
        _make_article("a.md", {"title": "A", "tags": ["Python", "core"]}),
        _make_article("b.md", {"title": "B", "tags": ["python", "core"]}),
    ]
    config = Config()
    issues = check(articles, config)
    tag_issues = [i for i in issues if "tag casing" in i.message.lower()]
    assert len(tag_issues) == 1
    assert "python" in tag_issues[0].message.lower()
    assert tag_issues[0].severity == Severity.WARNING


def test_no_tag_casing_issue_when_consistent():
    """No issues when all tags use the same casing."""
    articles = [
        _make_article("a.md", {"title": "A", "tags": ["python", "core"]}),
        _make_article("b.md", {"title": "B", "tags": ["python", "web"]}),
    ]
    config = Config()
    issues = check(articles, config)
    tag_issues = [i for i in issues if "tag casing" in i.message.lower()]
    assert len(tag_issues) == 0


def test_date_format_mismatch():
    """Detect mixed date formats across articles."""
    articles = [
        _make_article("a.md", {"title": "A", "created": "2024-01-15"}),
        _make_article("b.md", {"title": "B", "created": "2024-02-20"}),
        _make_article("c.md", {"title": "C", "created": "01/15/2024"}),
    ]
    config = Config()
    issues = check(articles, config)
    date_issues = [i for i in issues if "date format" in i.message.lower()]
    assert len(date_issues) >= 1
    # The minority format (MM/DD/YYYY) should be flagged
    assert any("MM/DD/YYYY" in i.message for i in date_issues)


def test_no_date_format_issue_when_consistent():
    """No issues when all dates use the same format."""
    articles = [
        _make_article("a.md", {"title": "A", "created": "2024-01-15"}),
        _make_article("b.md", {"title": "B", "created": "2024-02-20"}),
    ]
    config = Config()
    issues = check(articles, config)
    date_issues = [i for i in issues if "date format" in i.message.lower()]
    assert len(date_issues) == 0


def test_invalid_confidence_level():
    """Detect confidence levels not in the allowed set."""
    articles = [
        _make_article("a.md", {"title": "A", "confidence": "very-high"}),
    ]
    config = Config()
    issues = check(articles, config)
    conf_issues = [i for i in issues if "confidence" in i.message.lower()]
    assert len(conf_issues) == 1
    assert "very-high" in conf_issues[0].message
    assert conf_issues[0].severity == Severity.WARNING


def test_valid_confidence_level():
    """No issues for allowed confidence levels."""
    articles = [
        _make_article("a.md", {"title": "A", "confidence": "high"}),
        _make_article("b.md", {"title": "B", "confidence": "low"}),
    ]
    config = Config()
    issues = check(articles, config)
    conf_issues = [i for i in issues if "confidence" in i.message.lower()]
    assert len(conf_issues) == 0


def test_alias_casing_inconsistency():
    """Detect when the same alias appears with different casing."""
    articles = [
        _make_article("a.md", {"title": "A", "aliases": ["ML", "deep-learning"]}),
        _make_article("b.md", {"title": "B", "aliases": ["ml", "nlp"]}),
    ]
    config = Config()
    issues = check(articles, config)
    alias_issues = [i for i in issues if "alias casing" in i.message.lower()]
    assert len(alias_issues) == 1
    assert alias_issues[0].severity == Severity.INFO


def test_no_issues_when_fully_consistent():
    """A fully consistent set of articles should produce no issues."""
    articles = [
        _make_article(
            "a.md",
            {
                "title": "A",
                "tags": ["python", "core"],
                "created": "2024-01-15",
                "confidence": "high",
            },
        ),
        _make_article(
            "b.md",
            {
                "title": "B",
                "tags": ["python", "web"],
                "created": "2024-02-20",
                "confidence": "medium",
            },
        ),
    ]
    config = Config()
    issues = check(articles, config)
    assert len(issues) == 0


def test_healthy_wiki_no_consistency_issues(healthy_articles, default_config):
    """The healthy wiki fixture should have no consistency issues."""
    issues = check(healthy_articles, default_config)
    assert len(issues) == 0


def test_unhealthy_wiki_has_consistency_issues(unhealthy_articles, default_config):
    """The unhealthy wiki should have at least some consistency issues."""
    issues = check(unhealthy_articles, default_config)
    # The unhealthy wiki has 'very-high' confidence which is invalid
    conf_issues = [i for i in issues if "confidence" in i.message.lower()]
    assert len(conf_issues) >= 1
