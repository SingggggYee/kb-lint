"""Tests for the content check."""

from __future__ import annotations

from kb_lint.checks.content import check
from kb_lint.config import Config
from kb_lint.models import Severity
from kb_lint.scanner import scan


def test_healthy_wiki_no_content_issues(healthy_articles, default_config):
    issues = check(healthy_articles, default_config)
    # Healthy wiki should have no errors or warnings
    errors_warnings = [i for i in issues if i.severity in (Severity.ERROR, Severity.WARNING)]
    assert len(errors_warnings) == 0


def test_detects_thin_article(unhealthy_articles, default_config):
    issues = check(unhealthy_articles, default_config)
    thin_issues = [i for i in issues if "thin" in i.message.lower()]
    assert len(thin_issues) > 0
    # thin-article.md should be flagged
    assert any("thin-article" in str(i.file) for i in thin_issues)


def test_thin_article_is_warning(unhealthy_articles, default_config):
    issues = check(unhealthy_articles, default_config)
    thin_issues = [i for i in issues if "thin" in i.message.lower()]
    for issue in thin_issues:
        assert issue.severity == Severity.WARNING


def test_detects_placeholder(unhealthy_articles, default_config):
    issues = check(unhealthy_articles, default_config)
    placeholder_issues = [i for i in issues if "placeholder" in i.message.lower()]
    assert len(placeholder_issues) > 0


def test_placeholder_is_error(unhealthy_articles, default_config):
    issues = check(unhealthy_articles, default_config)
    placeholder_issues = [i for i in issues if "placeholder" in i.message.lower()]
    for issue in placeholder_issues:
        assert issue.severity == Severity.ERROR


def test_detects_empty_section(unhealthy_articles, default_config):
    issues = check(unhealthy_articles, default_config)
    empty_issues = [i for i in issues if "empty section" in i.message.lower()]
    assert len(empty_issues) > 0


def test_custom_min_words(tmp_path):
    (tmp_path / "short.md").write_text(
        "---\ntitle: Short\n---\n\nThis has exactly ten words in the body content area.\n"
    )
    config = Config(min_article_words=5)
    articles = scan(tmp_path, config)
    issues = check(articles, config)
    thin = [i for i in issues if "thin" in i.message.lower()]
    assert len(thin) == 0  # 10 words >= 5

    config2 = Config(min_article_words=50)
    issues2 = check(articles, config2)
    thin2 = [i for i in issues2 if "thin" in i.message.lower()]
    assert len(thin2) > 0  # 10 words < 50


def test_duplicate_titles(tmp_path, default_config):
    (tmp_path / "a.md").write_text(
        "---\ntitle: Same Title\n---\n" + "Content words " * 20 + "\n"
    )
    (tmp_path / "b.md").write_text(
        "---\ntitle: Same Title\n---\n" + "Content words " * 20 + "\n"
    )
    articles = scan(tmp_path, default_config)
    issues = check(articles, default_config)
    dup_issues = [i for i in issues if "duplicate title" in i.message.lower()]
    assert len(dup_issues) > 0
