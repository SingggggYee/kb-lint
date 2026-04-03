# kb-lint

**A linter for your LLM-compiled knowledge base.**

Run health checks over markdown wikis to catch broken links, missing metadata, orphan pages, thin articles, and structural inconsistencies — all without requiring an LLM.

Inspired by [Andrej Karpathy's approach](https://karpathy.ai/) to maintaining LLM-compiled wikis with automated quality checks.

## Installation

```bash
pip install kb-lint
```

## Quick Start

```bash
# Lint the current directory
kb-lint .

# Generate a health report
kb-lint ./my-wiki --report

# Auto-fix simple issues
kb-lint ./my-wiki --fix
```

## Example Output

```
 Knowledge Base Health Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Path:     ./wiki
  Articles: 47
  Links:    203

  3 errors  7 warnings  2 info

┌─────┬──────────────────────┬───────┬──────────────┬─────────────────────────────────────┐
│ Sev │ File                 │  Line │ Check        │ Message                             │
├─────┼──────────────────────┼───────┼──────────────┼─────────────────────────────────────┤
│ E   │ concepts/rlhf.md     │    23 │ links        │ Broken wiki-link: [[ppo-training]]  │
│ E   │ concepts/scaling.md  │     1 │ frontmatter  │ Missing required field: title        │
│ W   │ concepts/new-idea.md │     - │ content      │ Thin article: only 42 words          │
│ W   │ sources/paper-x.md   │     - │ orphans      │ Orphan article: no incoming links    │
│ I   │ concepts/nlp.md      │     - │ consistency  │ Inconsistent tag casing: NLP vs nlp  │
└─────┴──────────────────────┴───────┴──────────────┴─────────────────────────────────────┘

  2 issues can be auto-fixed with --fix

Health Score: 82/100
```

## Checks Reference

| Check | What it catches | Default severity | Auto-fixable? |
|-------|----------------|-----------------|---------------|
| `links` | Broken `[[wiki-links]]` | Error | No |
| `frontmatter` | Missing/invalid YAML frontmatter | Error/Info | Yes (add defaults) |
| `orphans` | Articles with no incoming links | Warning | No |
| `structure` | Non-kebab-case filenames, spaces | Error/Warning | Yes (rename) |
| `content` | Thin articles, `{{PLACEHOLDERS}}`, duplicate titles, empty sections | Error/Warning | No |
| `index` | Missing/extra entries in `_index.md` | Warning/Error | Yes (update index) |
| `consistency` | Inconsistent tags, dates, confidence levels | Warning | No |

## CLI Reference

```bash
# Basic lint
kb-lint [path]

# Output formats
kb-lint [path] --format terminal    # Rich colored output (default)
kb-lint [path] --format markdown    # Markdown report
kb-lint [path] --format json        # Machine-readable JSON

# Filter by severity
kb-lint [path] --severity error     # Only show errors
kb-lint [path] --severity warning   # Warnings and errors

# Run specific checks
kb-lint [path] --check links,frontmatter

# List available checks
kb-lint --list-checks

# Health report with score
kb-lint [path] --report

# CI mode (exit 1 on errors)
kb-lint [path] --ci

# Auto-fix
kb-lint [path] --fix
```

## Configuration

Configure via `.kblintrc.yml` in your wiki directory:

```yaml
required_frontmatter:
  - title
recommended_frontmatter:
  - tags
  - sources
  - created
  - confidence
min_article_words: 100
ignore_patterns:
  - _templates/**
  - drafts/**
recognized_directories:
  - concepts
  - sources
  - comparisons
allowed_confidence_levels:
  - high
  - medium
  - low
severity_threshold: info
```

Or in `pyproject.toml`:

```toml
[tool.kb-lint]
required_frontmatter = ["title"]
min_article_words = 100
```

## CI Integration

### GitHub Actions

```yaml
- name: Lint knowledge base
  run: |
    pip install kb-lint
    kb-lint ./wiki --ci
```

## Development

```bash
git clone https://github.com/SingggggYee/kb-lint
cd kb-lint
pip install -e ".[dev]"
pytest -v
ruff check src/ tests/
```

## License

MIT
