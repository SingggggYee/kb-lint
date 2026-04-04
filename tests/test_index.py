"""Tests for the index check."""

from __future__ import annotations

from pathlib import Path

from kb_lint.checks.index import check
from kb_lint.config import Config
from kb_lint.models import Severity
from kb_lint.scanner import scan


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _long_content() -> str:
    return "This is enough content to pass word count. " * 10


def test_missing_article_in_index(tmp_path):
    """Detect articles that exist but are not listed in _index.md."""
    _write(
        tmp_path / "_index.md",
        "---\ntitle: Index\n---\n\n- [[concept-a]]\n",
    )
    _write(
        tmp_path / "concept-a.md",
        f"---\ntitle: Concept A\n---\n\n{_long_content()}\n",
    )
    _write(
        tmp_path / "concept-b.md",
        f"---\ntitle: Concept B\n---\n\n{_long_content()}\n",
    )
    config = Config()
    articles = scan(tmp_path, config)
    issues = check(articles, config)
    missing = [i for i in issues if "Missing from index" in i.message]
    assert len(missing) == 1
    assert "concept-b" in missing[0].message


def test_extra_entry_in_index(tmp_path):
    """Detect index entries that point to non-existent articles."""
    _write(
        tmp_path / "_index.md",
        "---\ntitle: Index\n---\n\n- [[concept-a]]\n- [[nonexistent]]\n",
    )
    _write(
        tmp_path / "concept-a.md",
        f"---\ntitle: Concept A\n---\n\n{_long_content()}\n",
    )
    config = Config()
    articles = scan(tmp_path, config)
    issues = check(articles, config)
    extra = [i for i in issues if "non-existent" in i.message]
    assert len(extra) == 1
    assert "nonexistent" in extra[0].message
    assert extra[0].severity == Severity.ERROR


def test_duplicate_index_entries(tmp_path):
    """Detect duplicate entries in _index.md."""
    _write(
        tmp_path / "_index.md",
        "---\ntitle: Index\n---\n\n- [[concept-a]]\n- [[concept-a]]\n",
    )
    _write(
        tmp_path / "concept-a.md",
        f"---\ntitle: Concept A\n---\n\n{_long_content()}\n",
    )
    config = Config()
    articles = scan(tmp_path, config)
    issues = check(articles, config)
    dups = [i for i in issues if "Duplicate" in i.message]
    assert len(dups) == 1
    assert "2 times" in dups[0].message
    assert dups[0].severity == Severity.INFO
    assert dups[0].fixable is True


def test_no_index_file(tmp_path):
    """When there is no _index.md but articles exist, report a warning."""
    _write(
        tmp_path / "concept-a.md",
        f"---\ntitle: Concept A\n---\n\n{_long_content()}\n",
    )
    config = Config()
    articles = scan(tmp_path, config)
    issues = check(articles, config)
    no_index = [i for i in issues if "Missing index" in i.message]
    assert len(no_index) == 1
    assert no_index[0].severity == Severity.WARNING


def test_no_index_no_articles(tmp_path):
    """No index and no articles should produce no issues."""
    config = Config()
    articles = scan(tmp_path, config)
    issues = check(articles, config)
    assert len(issues) == 0


def test_perfect_index(tmp_path):
    """A perfect index listing all articles should produce no issues."""
    _write(
        tmp_path / "_index.md",
        "---\ntitle: Index\n---\n\n- [[concept-a]]\n- [[concept-b]]\n",
    )
    _write(
        tmp_path / "concept-a.md",
        f"---\ntitle: Concept A\n---\n\n{_long_content()}\n",
    )
    _write(
        tmp_path / "concept-b.md",
        f"---\ntitle: Concept B\n---\n\n{_long_content()}\n",
    )
    config = Config()
    articles = scan(tmp_path, config)
    issues = check(articles, config)
    assert len(issues) == 0


def test_healthy_wiki_index(healthy_articles, default_config):
    """The healthy wiki fixture should have no index issues."""
    issues = check(healthy_articles, default_config)
    assert len(issues) == 0


def test_unhealthy_wiki_index(unhealthy_articles, default_config):
    """The unhealthy wiki should have index issues (extra/missing/duplicate)."""
    issues = check(unhealthy_articles, default_config)
    assert len(issues) > 0
    # Should detect nonexistent-page
    assert any("nonexistent" in i.message.lower() for i in issues)
    # Should detect duplicate broken-links entry
    dups = [i for i in issues if "Duplicate" in i.message]
    assert len(dups) >= 1
