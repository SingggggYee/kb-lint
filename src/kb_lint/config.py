"""Configuration loading for kb-lint."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

VALID_CHECKS = frozenset(
    ["links", "frontmatter", "orphans", "structure", "content", "index", "consistency"]
)
VALID_SEVERITIES = frozenset(["error", "warning", "info"])

_DEFAULTS: dict[str, Any] = {
    "required_frontmatter": ["title"],
    "recommended_frontmatter": ["tags", "sources", "related", "created", "confidence"],
    "min_article_words": 100,
    "ignore_patterns": ["_templates/**", ".git/**", "node_modules/**"],
    "checks": ["links", "frontmatter", "orphans", "structure", "content", "index", "consistency"],
    "severity_threshold": "info",
    "check_severity": {},
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
    check_severity: dict[str, str] = field(default_factory=dict)
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
                with open(pyproject, "rb") as bf:
                    data = tomllib.load(bf)
                tool_cfg = data.get("tool", {}).get("kb-lint", {})
                if tool_cfg:
                    merged.update(tool_cfg)

        # Apply CLI overrides
        if overrides:
            merged.update(overrides)

        def _get(key: str) -> Any:
            return merged.get(key, _DEFAULTS[key])

        config = cls(
            required_frontmatter=_get("required_frontmatter"),
            recommended_frontmatter=_get("recommended_frontmatter"),
            min_article_words=int(_get("min_article_words")),
            ignore_patterns=_get("ignore_patterns"),
            checks=_get("checks"),
            severity_threshold=_get("severity_threshold"),
            recognized_directories=_get("recognized_directories"),
            allowed_confidence_levels=_get("allowed_confidence_levels"),
            check_severity=_get("check_severity"),
            check_external_urls=bool(merged.get("check_external_urls", False)),
        )
        config.validate()
        return config

    def validate(self) -> None:
        """Validate configuration values. Raises ValueError on invalid config."""
        # 1. checks must be valid names
        unknown = set(self.checks) - VALID_CHECKS
        if unknown:
            sorted_unknown = sorted(unknown)
            valid_sorted = sorted(VALID_CHECKS)
            raise ValueError(
                f"Unknown check(s): {', '.join(sorted_unknown)}. "
                f"Valid checks: {', '.join(valid_sorted)}"
            )

        # 2. severity_threshold
        if self.severity_threshold not in VALID_SEVERITIES:
            raise ValueError(
                f"Invalid severity_threshold '{self.severity_threshold}'. "
                f"Must be one of: {', '.join(sorted(VALID_SEVERITIES))}"
            )

        # 3. min_article_words must be a positive integer
        if not isinstance(self.min_article_words, int) or self.min_article_words <= 0:
            raise ValueError(
                f"min_article_words must be a positive integer, got {self.min_article_words}"
            )

        # 4. required_frontmatter and recommended_frontmatter must be lists of strings
        for field_name in ("required_frontmatter", "recommended_frontmatter"):
            value = getattr(self, field_name)
            if not isinstance(value, list) or not all(isinstance(s, str) for s in value):
                raise ValueError(
                    f"{field_name} must be a list of strings, "
                    f"got {type(value).__name__}"
                )

        # 5. check_severity keys must be valid check names, values must be valid severities
        if self.check_severity:
            unknown_checks = set(self.check_severity.keys()) - VALID_CHECKS
            if unknown_checks:
                raise ValueError(
                    f"Unknown check(s) in check_severity: {', '.join(sorted(unknown_checks))}. "
                    f"Valid checks: {', '.join(sorted(VALID_CHECKS))}"
                )
            for check_name, sev in self.check_severity.items():
                if sev not in VALID_SEVERITIES:
                    raise ValueError(
                        f"Invalid severity '{sev}' for check '{check_name}' in check_severity. "
                        f"Must be one of: {', '.join(sorted(VALID_SEVERITIES))}"
                    )

        # 6. ignore_patterns must be a list of strings
        if not isinstance(self.ignore_patterns, list) or not all(
            isinstance(s, str) for s in self.ignore_patterns
        ):
            raise ValueError(
                "ignore_patterns must be a list of strings, "
                f"got {type(self.ignore_patterns).__name__}"
            )


__all__ = ["Config"]
