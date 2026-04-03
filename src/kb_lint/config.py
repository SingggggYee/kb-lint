"""Configuration loading for kb-lint."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_DEFAULTS: dict[str, Any] = {
    "required_frontmatter": ["title"],
    "recommended_frontmatter": ["tags", "sources", "related", "created", "confidence"],
    "min_article_words": 100,
    "ignore_patterns": ["_templates/**", ".git/**", "node_modules/**"],
    "checks": ["links", "frontmatter", "orphans", "structure", "content", "index", "consistency"],
    "severity_threshold": "info",
    "recognized_directories": ["concepts", "sources", "comparisons"],
    "allowed_confidence_levels": ["high", "medium", "low"],
}


@dataclass
class Config:
    """Resolved configuration for a kb-lint run."""

    required_frontmatter: list[str] = field(
        default_factory=lambda: list(_DEFAULTS["required_frontmatter"])
    )
    recommended_frontmatter: list[str] = field(
        default_factory=lambda: list(_DEFAULTS["recommended_frontmatter"])
    )
    min_article_words: int = _DEFAULTS["min_article_words"]
    ignore_patterns: list[str] = field(
        default_factory=lambda: list(_DEFAULTS["ignore_patterns"])
    )
    checks: list[str] = field(
        default_factory=lambda: list(_DEFAULTS["checks"])
    )
    severity_threshold: str = _DEFAULTS["severity_threshold"]
    recognized_directories: list[str] = field(
        default_factory=lambda: list(_DEFAULTS["recognized_directories"])
    )
    allowed_confidence_levels: list[str] = field(
        default_factory=lambda: list(_DEFAULTS["allowed_confidence_levels"])
    )
    check_external_urls: bool = False

    @classmethod
    def load(cls, wiki_path: Path, overrides: dict[str, Any] | None = None) -> Config:
        """Load config by merging defaults, file config, and CLI overrides."""
        merged: dict[str, Any] = dict(_DEFAULTS)

        # Try .kblintrc.yml in the wiki directory
        rc_path = wiki_path / ".kblintrc.yml"
        if rc_path.is_file():
            with open(rc_path) as f:
                file_cfg = yaml.safe_load(f)
            if isinstance(file_cfg, dict):
                merged.update(file_cfg)

        # Try pyproject.toml [tool.kb-lint]
        pyproject = wiki_path / "pyproject.toml"
        if pyproject.is_file():
            try:
                import tomllib  # type: ignore[import-not-found]
            except ImportError:
                try:
                    import tomli as tomllib  # type: ignore[no-redef]
                except ImportError:
                    tomllib = None  # type: ignore[assignment]
            if tomllib is not None:
                with open(pyproject, "rb") as f:
                    data = tomllib.load(f)
                tool_cfg = data.get("tool", {}).get("kb-lint", {})
                if tool_cfg:
                    merged.update(tool_cfg)

        # Apply CLI overrides
        if overrides:
            merged.update(overrides)

        def _get(key: str) -> Any:
            return merged.get(key, _DEFAULTS[key])

        return cls(
            required_frontmatter=_get("required_frontmatter"),
            recommended_frontmatter=_get("recommended_frontmatter"),
            min_article_words=int(_get("min_article_words")),
            ignore_patterns=_get("ignore_patterns"),
            checks=_get("checks"),
            severity_threshold=_get("severity_threshold"),
            recognized_directories=_get("recognized_directories"),
            allowed_confidence_levels=_get("allowed_confidence_levels"),
            check_external_urls=bool(merged.get("check_external_urls", False)),
        )


__all__ = ["Config"]
