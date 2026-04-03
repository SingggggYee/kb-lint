# kb-lint

A Python CLI linter for markdown knowledge bases.

## Build & Test

```bash
pip install -e ".[dev]"
pytest -v
ruff check src/ tests/
```

## Project Layout

- `src/kb_lint/` — main package
  - `cli.py` — Click CLI entry point
  - `scanner.py` — directory scanner, builds article inventory
  - `checks/` — individual check modules (links, frontmatter, orphans, etc.)
  - `models.py` — Issue, Severity, Article, CheckResult dataclasses
  - `reporter.py` — output formatters (terminal/markdown/JSON)
  - `fixer.py` — auto-fix for simple issues
  - `config.py` — configuration loading
- `tests/` — pytest tests with tmp_path fixtures
- `examples/` — sample healthy and unhealthy wikis

## Conventions

- Python 3.10+ with type hints throughout
- Each check module exports `def check(articles, config) -> list[Issue]`
- Use `from __future__ import annotations` in all modules
- Run `ruff check` before committing
