"""Tests for the reporter output formatters."""

from __future__ import annotations

import json
from pathlib import Path

from kb_lint.models import Article, Issue, Severity
from kb_lint.reporter import format_json, format_markdown, format_terminal


def _make_article(rel: str = "test.md") -> Article:
    return Article(
        path=Path("/wiki") / rel,
        relative_path=Path(rel),
        frontmatter={"title": "Test"},
        content="Test content " * 20,
        raw="---\ntitle: Test\n---\n" + "Test content " * 20,
        title="Test",
        wiki_links=[],
        word_count=40,
    )


def _make_issue(
    sev: Severity = Severity.WARNING,
    msg: str = "Test issue",
    file: str = "test.md",
) -> Issue:
    return Issue(
        check="test",
        severity=sev,
        file=Path(file),
        line=5,
        message=msg,
        suggestion="Fix it",
        fixable=False,
    )


def test_terminal_no_issues(capsys):
    """Terminal format with no issues should show healthy message."""
    articles = [_make_article()]
    format_terminal([], articles, Path("/wiki"), is_report=True)
    captured = capsys.readouterr()
    assert "healthy" in captured.out.lower() or "no issues" in captured.out.lower()


def test_terminal_with_issues(capsys):
    """Terminal format with issues should show the table."""
    articles = [_make_article()]
    issues = [_make_issue(Severity.ERROR, "Broken link"), _make_issue(Severity.WARNING, "Thin")]
    format_terminal(issues, articles, Path("/wiki"), is_report=True)
    captured = capsys.readouterr()
    assert "1 error" in captured.out.lower() or "1 error" in captured.out
    assert "Health Score" in captured.out


def test_markdown_format():
    articles = [_make_article()]
    issues = [_make_issue(Severity.ERROR, "Broken link")]
    output = format_markdown(issues, articles, Path("/wiki"))
    assert "# Knowledge Base Health Report" in output
    assert "Broken link" in output
    assert "ERROR" in output
    assert "|" in output  # table


def test_markdown_no_issues():
    articles = [_make_article()]
    output = format_markdown([], articles, Path("/wiki"))
    assert "No issues found" in output
    assert "100/100" in output


def test_json_format():
    articles = [_make_article()]
    issues = [
        _make_issue(Severity.ERROR, "Error one"),
        _make_issue(Severity.WARNING, "Warning one"),
    ]
    output = format_json(issues, articles, Path("/wiki"))
    data = json.loads(output)

    assert data["articles"] == 1
    assert data["summary"]["errors"] == 1
    assert data["summary"]["warnings"] == 1
    assert len(data["issues"]) == 2
    assert data["health_score"] <= 100


def test_json_no_issues():
    articles = [_make_article()]
    output = format_json([], articles, Path("/wiki"))
    data = json.loads(output)
    assert data["health_score"] == 100
    assert data["summary"]["errors"] == 0
    assert len(data["issues"]) == 0


def test_health_score_decreases_with_errors():
    articles = [_make_article()]
    no_issues = json.loads(format_json([], articles, Path("/wiki")))
    with_errors = json.loads(
        format_json(
            [_make_issue(Severity.ERROR)] * 5,
            articles,
            Path("/wiki"),
        )
    )
    assert no_issues["health_score"] > with_errors["health_score"]
