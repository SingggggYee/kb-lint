"""Tests for the structure check."""

from __future__ import annotations

from kb_lint.checks.structure import check
from kb_lint.models import Severity
from kb_lint.scanner import scan


def test_healthy_wiki_no_structure_errors(healthy_articles, default_config):
    issues = check(healthy_articles, default_config)
    errors = [i for i in issues if i.severity == Severity.ERROR]
    assert len(errors) == 0


def test_detects_spaces_in_filename(unhealthy_articles, default_config):
    issues = check(unhealthy_articles, default_config)
    space_issues = [i for i in issues if "spaces" in i.message.lower()]
    assert len(space_issues) > 0


def test_space_filename_is_error(unhealthy_articles, default_config):
    issues = check(unhealthy_articles, default_config)
    space_issues = [i for i in issues if "spaces" in i.message.lower()]
    for issue in space_issues:
        assert issue.severity == Severity.ERROR
        assert issue.fixable


def test_kebab_case_validation(tmp_path, default_config):
    (tmp_path / "CamelCase.md").write_text("---\ntitle: Test\n---\nContent words " * 20 + "\n")
    articles = scan(tmp_path, default_config)
    issues = check(articles, default_config)
    kebab_issues = [i for i in issues if "kebab" in i.message.lower()]
    assert len(kebab_issues) > 0


def test_index_file_allowed(tmp_path, default_config):
    """_index.md should not be flagged for naming."""
    (tmp_path / "_index.md").write_text("---\ntitle: Index\n---\n# Index\n")
    articles = scan(tmp_path, default_config)
    issues = check(articles, default_config)
    assert not any("_index" in i.message for i in issues)


def test_unrecognized_directory_info(tmp_path, default_config):
    """Articles in unrecognized directories get an info issue."""
    (tmp_path / "random-dir").mkdir()
    (tmp_path / "random-dir" / "article.md").write_text("---\ntitle: Test\n---\nContent\n")
    articles = scan(tmp_path, default_config)
    issues = check(articles, default_config)
    dir_issues = [i for i in issues if "unrecognized directory" in i.message.lower()]
    assert len(dir_issues) > 0
    assert dir_issues[0].severity == Severity.INFO


def test_duplicate_stems(tmp_path, default_config):
    (tmp_path / "dir-a").mkdir()
    (tmp_path / "dir-b").mkdir()
    (tmp_path / "dir-a" / "article.md").write_text("---\ntitle: A\n---\nContent\n")
    (tmp_path / "dir-b" / "article.md").write_text("---\ntitle: B\n---\nContent\n")
    articles = scan(tmp_path, default_config)
    issues = check(articles, default_config)
    dup_issues = [i for i in issues if "duplicate" in i.message.lower()]
    assert len(dup_issues) > 0
