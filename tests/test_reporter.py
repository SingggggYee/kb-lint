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


# ── Edge case tests ──────────────────────────────────────────────────


class TestEmptyInput:
    """Zero issues AND zero articles should produce valid output."""

    def test_terminal_empty(self, capsys):
        format_terminal([], [], Path("/wiki"), is_report=True)
        captured = capsys.readouterr()
        assert "healthy" in captured.out.lower() or "no issues" in captured.out.lower()
        assert "Health Score" in captured.out
        assert "Articles" in captured.out

    def test_markdown_empty(self):
        output = format_markdown([], [], Path("/wiki"))
        assert "# Knowledge Base Health Report" in output
        assert "**Articles**: 0" in output
        assert "**Links**: 0" in output
        assert "100/100" in output
        assert "No issues found" in output

    def test_json_empty(self):
        output = format_json([], [], Path("/wiki"))
        data = json.loads(output)
        assert data["articles"] == 0
        assert data["links"] == 0
        assert data["health_score"] == 100
        assert data["summary"]["errors"] == 0
        assert data["summary"]["warnings"] == 0
        assert data["summary"]["info"] == 0
        assert data["issues"] == []


class TestUnicodeMessages:
    """Unicode in file paths and messages must render correctly."""

    def test_terminal_unicode(self, capsys):
        issues = [
            _make_issue(Severity.WARNING, "缺少标题字段", "笔记/日记.md"),
            _make_issue(Severity.ERROR, "Link to 🚀 missing", "docs/emoji🎉.md"),
        ]
        articles = [_make_article("笔记/日记.md")]
        format_terminal(issues, articles, Path("/wiki"), is_report=False)
        captured = capsys.readouterr()
        assert "缺少标题字段" in captured.out
        assert "日记" in captured.out

    def test_markdown_unicode(self):
        issues = [
            _make_issue(Severity.WARNING, "缺少标题字段", "笔记/日记.md"),
            _make_issue(Severity.INFO, "Contains emoji 🎉✨", "docs/fun.md"),
        ]
        output = format_markdown(issues, [_make_article()], Path("/wiki"))
        assert "缺少标题字段" in output
        assert "🎉✨" in output
        assert "日记" in output

    def test_json_unicode(self):
        issues = [
            _make_issue(Severity.ERROR, "リンク切れ：対象記事が見つかりません", "ノート/概要.md"),
            _make_issue(Severity.WARNING, "Emoji path 🔥", "docs/emoji🎉.md"),
        ]
        output = format_json(issues, [_make_article()], Path("/wiki"))
        data = json.loads(output)
        # Verify Unicode is preserved (not ASCII-escaped)
        assert "リンク切れ" in output
        assert "🔥" in output
        assert (
            data["issues"][0]["message"] == "Emoji path 🔥"
            or data["issues"][1]["message"] == "Emoji path 🔥"
        )


class TestLongFilePaths:
    """Paths with 200+ characters must not crash or produce malformed output."""

    LONG_PATH = "a/" * 100 + "very_long_file.md"  # ~300 chars

    def test_terminal_long_path(self, capsys):
        issues = [_make_issue(Severity.WARNING, "Thin article", TestLongFilePaths.LONG_PATH)]
        format_terminal(issues, [_make_article()], Path("/wiki"))
        captured = capsys.readouterr()
        # Should not crash; path is folded across lines by Rich
        assert "file.md" in captured.out
        assert "Thin article" in captured.out

    def test_markdown_long_path(self):
        issues = [_make_issue(Severity.WARNING, "Thin article", TestLongFilePaths.LONG_PATH)]
        output = format_markdown(issues, [_make_article()], Path("/wiki"))
        assert "very_long_file" in output
        # Table structure must still be intact
        assert output.count("|") >= 5  # at least one data row

    def test_json_long_path(self):
        issues = [_make_issue(Severity.WARNING, "Thin article", TestLongFilePaths.LONG_PATH)]
        output = format_json(issues, [_make_article()], Path("/wiki"))
        data = json.loads(output)  # Must be valid JSON
        assert "very_long_file" in data["issues"][0]["file"]


class TestJsonSpecialCharacters:
    """JSON output must be valid even with tricky characters in messages."""

    def test_json_with_quotes_and_backslashes(self):
        issues = [
            _make_issue(Severity.ERROR, 'Missing "title" in frontmatter', "test.md"),
            _make_issue(Severity.WARNING, "Path has backslash: C:\\Users\\test", "test.md"),
        ]
        output = format_json(issues, [_make_article()], Path("/wiki"))
        data = json.loads(output)  # Must not raise
        assert len(data["issues"]) == 2
        assert '"title"' in data["issues"][0]["message"]
        assert "C:\\Users\\test" in data["issues"][1]["message"]

    def test_json_with_newlines_and_tabs(self):
        issues = [_make_issue(Severity.INFO, "Line1\nLine2\tTabbed", "test.md")]
        output = format_json(issues, [_make_article()], Path("/wiki"))
        data = json.loads(output)
        assert "Line1\nLine2\tTabbed" == data["issues"][0]["message"]

    def test_json_with_angle_brackets_and_ampersand(self):
        issues = [_make_issue(Severity.WARNING, "<script>alert('xss')</script> & more", "test.md")]
        output = format_json(issues, [_make_article()], Path("/wiki"))
        data = json.loads(output)
        assert "<script>" in data["issues"][0]["message"]


class TestMarkdownPipeEscaping:
    """Pipe characters in messages must not break markdown table rows."""

    def test_pipe_in_message(self):
        issues = [_make_issue(Severity.WARNING, "Choice A | Choice B", "test.md")]
        output = format_markdown(issues, [_make_article()], Path("/wiki"))
        # The raw pipe should be escaped
        assert "Choice A \\| Choice B" in output
        # Table header has exactly 6 pipes per row; data rows should too
        data_lines = [line for line in output.split("\n") if line.startswith("| WARNING")]
        assert len(data_lines) == 1
        # Count unescaped pipes (not preceded by backslash)
        import re

        unescaped = re.findall(r"(?<!\\)\|", data_lines[0])
        assert len(unescaped) == 6  # exactly 6 column delimiters

    def test_pipe_in_filepath(self):
        issues = [_make_issue(Severity.ERROR, "Bad", "dir|name/file.md")]
        output = format_markdown(issues, [_make_article()], Path("/wiki"))
        assert "dir\\|name" in output
