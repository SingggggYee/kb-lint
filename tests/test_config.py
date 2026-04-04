"""Tests for config loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from kb_lint.config import Config
from kb_lint.models import Article, Severity


def test_default_config_values():
    """Default Config() should have the expected default values."""
    config = Config()
    assert "title" in config.required_frontmatter
    assert config.min_article_words == 100
    assert "links" in config.checks
    assert "consistency" in config.checks
    assert config.severity_threshold == "info"
    assert "high" in config.allowed_confidence_levels
    assert "medium" in config.allowed_confidence_levels
    assert "low" in config.allowed_confidence_levels
    assert config.check_external_urls is False


def test_kblintrc_yml_parsing(tmp_path):
    """Config.load should read .kblintrc.yml and override defaults."""
    rc = tmp_path / ".kblintrc.yml"
    rc.write_text("min_article_words: 50\nseverity_threshold: warning\n")
    config = Config.load(tmp_path)
    assert config.min_article_words == 50
    assert config.severity_threshold == "warning"
    # Non-overridden values stay default
    assert "title" in config.required_frontmatter


def test_pyproject_toml_parsing(tmp_path):
    """Config.load should read [tool.kb-lint] from pyproject.toml."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[tool.kb-lint]\nmin_article_words = 200\ncheck_external_urls = true\n'
    )
    config = Config.load(tmp_path)
    assert config.min_article_words == 200
    assert config.check_external_urls is True


def test_override_precedence(tmp_path):
    """CLI overrides > file config > defaults."""
    rc = tmp_path / ".kblintrc.yml"
    rc.write_text("min_article_words: 50\nseverity_threshold: warning\n")
    config = Config.load(tmp_path, overrides={"min_article_words": 25})
    # CLI override wins over .kblintrc.yml
    assert config.min_article_words == 25
    # File config still applies for non-overridden keys
    assert config.severity_threshold == "warning"


def test_missing_config_file(tmp_path):
    """Config.load with no config files should return defaults."""
    config = Config.load(tmp_path)
    default = Config()
    assert config.min_article_words == default.min_article_words
    assert config.required_frontmatter == default.required_frontmatter
    assert config.checks == default.checks


def test_invalid_kblintrc_yml(tmp_path):
    """Config.load should handle non-dict YAML gracefully."""
    rc = tmp_path / ".kblintrc.yml"
    rc.write_text("just a string\n")
    # Should not raise — non-dict is ignored
    config = Config.load(tmp_path)
    assert config.min_article_words == 100


def test_pyproject_without_kb_lint_section(tmp_path):
    """pyproject.toml without [tool.kb-lint] should be ignored."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[tool.other]\nfoo = "bar"\n')
    config = Config.load(tmp_path)
    assert config.min_article_words == 100


def test_kblintrc_overrides_list_fields(tmp_path):
    """Config file can override list fields like checks."""
    rc = tmp_path / ".kblintrc.yml"
    rc.write_text("checks:\n  - links\n  - frontmatter\n")
    config = Config.load(tmp_path)
    assert config.checks == ["links", "frontmatter"]


def test_pyproject_takes_precedence_over_kblintrc(tmp_path):
    """When both config files exist, pyproject.toml overrides .kblintrc.yml."""
    rc = tmp_path / ".kblintrc.yml"
    rc.write_text("min_article_words: 50\n")
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[tool.kb-lint]\nmin_article_words = 200\n')
    config = Config.load(tmp_path)
    # pyproject.toml is loaded after .kblintrc.yml, so it wins
    assert config.min_article_words == 200


# --- Validation tests ---


class TestConfigValidation:
    """Tests for Config.validate()."""

    def test_valid_config_passes(self):
        """Default config should pass validation without errors."""
        config = Config()
        config.validate()  # should not raise

    def test_unknown_check_raises(self, tmp_path):
        """Unknown check name should raise ValueError."""
        rc = tmp_path / ".kblintrc.yml"
        rc.write_text("checks:\n  - links\n  - foo\n")
        with pytest.raises(ValueError, match="Unknown check.*foo.*Valid checks"):
            Config.load(tmp_path)

    def test_invalid_severity_raises(self, tmp_path):
        """Invalid severity_threshold should raise ValueError."""
        rc = tmp_path / ".kblintrc.yml"
        rc.write_text("severity_threshold: critical\n")
        with pytest.raises(ValueError, match="Invalid severity_threshold.*critical"):
            Config.load(tmp_path)

    def test_negative_min_article_words_raises(self, tmp_path):
        """Negative min_article_words should raise ValueError."""
        rc = tmp_path / ".kblintrc.yml"
        rc.write_text("min_article_words: -5\n")
        with pytest.raises(ValueError, match="min_article_words must be a positive integer"):
            Config.load(tmp_path)

    def test_zero_min_article_words_raises(self, tmp_path):
        """Zero min_article_words should raise ValueError."""
        rc = tmp_path / ".kblintrc.yml"
        rc.write_text("min_article_words: 0\n")
        with pytest.raises(ValueError, match="min_article_words must be a positive integer"):
            Config.load(tmp_path)

    def test_non_list_required_frontmatter_raises(self):
        """Non-list required_frontmatter should raise ValueError."""
        config = Config(required_frontmatter="title")  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="required_frontmatter must be a list of strings"):
            config.validate()

    def test_non_list_recommended_frontmatter_raises(self):
        """Non-list recommended_frontmatter should raise ValueError."""
        config = Config(recommended_frontmatter="tags")  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="recommended_frontmatter must be a list of strings"):
            config.validate()

    def test_non_list_ignore_patterns_raises(self):
        """Non-list ignore_patterns should raise ValueError."""
        config = Config(ignore_patterns="*.md")  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="ignore_patterns must be a list of strings"):
            config.validate()

    def test_valid_custom_config_passes(self, tmp_path):
        """A valid custom config should pass validation."""
        rc = tmp_path / ".kblintrc.yml"
        rc.write_text(
            "checks:\n  - links\n  - orphans\n"
            "severity_threshold: error\n"
            "min_article_words: 50\n"
        )
        config = Config.load(tmp_path)
        assert config.checks == ["links", "orphans"]
        assert config.severity_threshold == "error"
        assert config.min_article_words == 50


class TestCheckSeverityOverride:
    """Tests for per-check severity override via check_severity config."""

    def test_per_check_severity_override_works(self, tmp_path):
        """check_severity should override issue severity after checks run."""
        from kb_lint.checks import run_checks

        # Create a minimal article that will trigger orphans check
        article = Article(
            path=tmp_path / "test.md",
            relative_path=Path("test.md"),
            frontmatter={"title": "Test"},
            content="Some content " * 20,
            raw="---\ntitle: Test\n---\n" + "Some content " * 20,
            title="Test",
            wiki_links=[],
            word_count=200,
        )
        config = Config(
            checks=["orphans"],
            check_severity={"orphans": "info"},
        )
        issues = run_checks([article], config)
        # All orphan issues should be overridden to INFO
        for issue in issues:
            if issue.check == "orphans":
                assert issue.severity == Severity.INFO

    def test_invalid_check_name_in_check_severity_raises(self, tmp_path):
        """Unknown check name in check_severity should raise ValueError."""
        rc = tmp_path / ".kblintrc.yml"
        rc.write_text("check_severity:\n  nonexistent: info\n")
        with pytest.raises(ValueError, match="Unknown check.*check_severity.*nonexistent"):
            Config.load(tmp_path)

    def test_invalid_severity_value_in_check_severity_raises(self, tmp_path):
        """Invalid severity value in check_severity should raise ValueError."""
        rc = tmp_path / ".kblintrc.yml"
        rc.write_text("check_severity:\n  orphans: critical\n")
        with pytest.raises(ValueError, match="Invalid severity.*critical.*check_severity"):
            Config.load(tmp_path)

    def test_overridden_severity_affects_filtering(self, tmp_path):
        """Issues overridden to lower severity should be filterable by threshold."""
        from kb_lint.checks import run_checks

        article = Article(
            path=tmp_path / "test.md",
            relative_path=Path("test.md"),
            frontmatter={"title": "Test"},
            content="Some content " * 20,
            raw="---\ntitle: Test\n---\n" + "Some content " * 20,
            title="Test",
            wiki_links=[],
            word_count=200,
        )
        config = Config(
            checks=["orphans"],
            check_severity={"orphans": "info"},
            severity_threshold="warning",
        )
        issues = run_checks([article], config)
        # Filter by threshold (as the main CLI would do)
        threshold = Severity[config.severity_threshold.upper()]
        filtered = [i for i in issues if i.severity >= threshold]
        # Orphan issues overridden to INFO should be filtered out by WARNING threshold
        orphan_issues = [i for i in filtered if i.check == "orphans"]
        assert orphan_issues == []

    def test_default_check_severity_is_empty(self):
        """Default Config should have empty check_severity."""
        config = Config()
        assert config.check_severity == {}

    def test_check_severity_from_kblintrc(self, tmp_path):
        """check_severity should load from .kblintrc.yml."""
        rc = tmp_path / ".kblintrc.yml"
        rc.write_text("check_severity:\n  orphans: info\n  links: error\n")
        config = Config.load(tmp_path)
        assert config.check_severity == {"orphans": "info", "links": "error"}
