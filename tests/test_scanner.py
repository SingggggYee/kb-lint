"""Tests for the scanner module."""

from __future__ import annotations

from pathlib import Path

from kb_lint.config import Config
from kb_lint.scanner import scan


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_basic_markdown_scanning(tmp_path):
    """Scanner should find all .md files recursively."""
    _write(tmp_path / "a.md", "---\ntitle: A\n---\n\nContent A.\n")
    _write(tmp_path / "sub" / "b.md", "---\ntitle: B\n---\n\nContent B.\n")
    config = Config()
    articles = scan(tmp_path, config)
    assert len(articles) == 2
    stems = {a.path.stem for a in articles}
    assert stems == {"a", "b"}


def test_frontmatter_extraction(tmp_path):
    """Scanner should parse YAML frontmatter into a dict."""
    _write(
        tmp_path / "article.md",
        "---\ntitle: My Article\ntags: [python, testing]\nconfidence: high\n---\n\nBody.\n",
    )
    config = Config()
    articles = scan(tmp_path, config)
    assert len(articles) == 1
    a = articles[0]
    assert a.frontmatter["title"] == "My Article"
    assert a.frontmatter["tags"] == ["python", "testing"]
    assert a.frontmatter["confidence"] == "high"
    assert a.title == "My Article"


def test_wiki_link_extraction(tmp_path):
    """Scanner should extract [[wiki-links]] from content."""
    _write(
        tmp_path / "article.md",
        "---\ntitle: Test\n---\n\nSee [[concept-a]] and [[concept-b]].\n",
    )
    config = Config()
    articles = scan(tmp_path, config)
    assert len(articles) == 1
    assert set(articles[0].wiki_links) == {"concept-a", "concept-b"}


def test_word_count_calculation(tmp_path):
    """Scanner should count words in the content (excluding frontmatter)."""
    body = "one two three four five"
    _write(
        tmp_path / "article.md",
        f"---\ntitle: Test\n---\n\n{body}\n",
    )
    config = Config()
    articles = scan(tmp_path, config)
    assert len(articles) == 1
    assert articles[0].word_count == 5


def test_binary_file_skipping(tmp_path):
    """Scanner should skip binary files even if they have .md extension."""
    _write(tmp_path / "good.md", "---\ntitle: Good\n---\n\nContent.\n")
    binary_path = tmp_path / "binary.md"
    binary_path.write_bytes(b"---\ntitle: Bin\n---\n\x00binary content\n")
    config = Config()
    articles = scan(tmp_path, config)
    assert len(articles) == 1
    assert articles[0].path.stem == "good"


def test_empty_directory(tmp_path):
    """Scanner should return an empty list for an empty directory."""
    config = Config()
    articles = scan(tmp_path, config)
    assert articles == []


def test_no_frontmatter_fallback_title(tmp_path):
    """Without frontmatter, title should fall back to first H1 or filename."""
    _write(tmp_path / "my-article.md", "# My Custom Title\n\nSome content.\n")
    config = Config()
    articles = scan(tmp_path, config)
    assert len(articles) == 1
    assert articles[0].title == "My Custom Title"
    assert articles[0].frontmatter == {}


def test_title_from_filename(tmp_path):
    """Without frontmatter or H1, title should derive from filename."""
    _write(tmp_path / "cool-topic.md", "Just some content, no heading.\n")
    config = Config()
    articles = scan(tmp_path, config)
    assert len(articles) == 1
    assert articles[0].title == "Cool Topic"


def test_ignore_patterns(tmp_path):
    """Scanner should respect ignore patterns from config."""
    _write(tmp_path / "good.md", "---\ntitle: Good\n---\n\nContent.\n")
    _write(tmp_path / "_templates" / "tpl.md", "---\ntitle: Tpl\n---\n\nTemplate.\n")
    config = Config()
    articles = scan(tmp_path, config)
    assert len(articles) == 1
    assert articles[0].path.stem == "good"


def test_relative_path_is_set(tmp_path):
    """Each article should have a relative_path set correctly."""
    _write(tmp_path / "sub" / "article.md", "---\ntitle: A\n---\n\nContent.\n")
    config = Config()
    articles = scan(tmp_path, config)
    assert len(articles) == 1
    assert articles[0].relative_path == Path("sub") / "article.md"


def test_nonexistent_directory():
    """Scanning a nonexistent path should return an empty list."""
    config = Config()
    articles = scan(Path("/nonexistent/path/abc123"), config)
    assert articles == []
