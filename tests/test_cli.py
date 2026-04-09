"""CLI integration tests using Click's CliRunner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from kb_lint.cli import main


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def healthy_wiki_dir(tmp_path: Path) -> Path:
    """A small healthy wiki with valid articles and links."""
    _write(
        tmp_path / "_index.md",
        """\
---
title: "Index"
---

# Index

- [[concept-a]]
- [[concept-b]]
""",
    )
    _write(
        tmp_path / "concepts" / "concept-a.md",
        """\
---
title: "Concept A"
tags: [core, fundamentals]
created: 2024-01-15
confidence: high
sources: ["https://example.com"]
related: [concept-b]
---

# Concept A

Concept A is a foundational idea. It connects to many other parts
of the knowledge base and serves as an entry point for newcomers.
This article covers the key ideas behind Concept A, its history,
and how it relates to other concepts in the system. The field has
grown significantly since its inception, with applications across
domains including natural language processing and computer vision.
Researchers have published extensively on Concept A, exploring its
theoretical properties, practical implementations, and connections
to adjacent fields. The core insight behind Concept A is that
complex systems can be decomposed into simpler components that
interact in predictable ways. This decomposition enables modular
reasoning and incremental development of larger systems.

See also [[concept-b]] for practical details.
""",
    )
    _write(
        tmp_path / "concepts" / "concept-b.md",
        """\
---
title: "Concept B"
tags: [core, implementation]
created: 2024-01-20
confidence: high
sources: ["https://example.com/b"]
related: [concept-a]
---

# Concept B

Concept B builds on [[concept-a]] and provides implementation
strategies. It is the practical counterpart to the theoretical
foundations laid out in Concept A. Engineers use Concept B daily
when building systems that require the properties described by
Concept A. This article walks through the main patterns and best
practices that have emerged from real-world use over the past
several years. The implementation typically follows a three-phase
approach: foundation setup, core logic implementation, and
production optimization. Each phase builds on the previous one,
allowing teams to adopt Concept B incrementally without disrupting
existing workflows. Testing and monitoring are essential throughout
the process to ensure correctness and performance.
""",
    )
    return tmp_path


@pytest.fixture
def unhealthy_wiki_dir(tmp_path: Path) -> Path:
    """A wiki with various issues: broken links, thin articles, bad names, etc."""
    _write(
        tmp_path / "_index.md",
        """\
---
title: "Index"
---

# Index

- [[broken-links]]
- [[thin-article]]
- [[nonexistent-page]]
- [[broken-links]]
""",
    )
    _write(
        tmp_path / "concepts" / "broken-links.md",
        """\
---
title: "Broken Links"
tags: [test]
created: 2024-01-15
confidence: high
---

# Broken Links

See [[does-not-exist]] for more info.

Also check [[another-missing]].

But [[thin-article]] is fine.
""",
    )
    _write(
        tmp_path / "concepts" / "thin-article.md",
        """\
---
title: "Thin Article"
tags: test
confidence: very-high
created: 01/15/2024
---

# Thin Article

Too short.

## Empty Section

## Another Section

Some content here.
""",
    )
    _write(
        tmp_path / "concepts" / "no-frontmatter.md",
        """\
# No Frontmatter

This article has no YAML frontmatter block. It should be flagged
for missing required fields. The content itself is long enough to
not be considered thin, with enough words to pass the minimum word
count threshold for articles in the knowledge base system.
""",
    )
    _write(
        tmp_path / "concepts" / "orphan.md",
        """\
---
title: "Orphan"
tags: [test]
created: 2024-02-01
confidence: low
---

# Orphan

Nobody links to this article, making it an orphan in the knowledge
graph. The linter should detect this and report a warning. Orphan
articles reduce the discoverability of knowledge and indicate gaps
in the link structure of the wiki.
""",
    )
    _write(
        tmp_path / "concepts" / "Bad Name.md",
        """\
---
title: "Bad Name"
tags: [test]
created: 2024-03-01
confidence: medium
---

# Bad Name

This file has spaces in its filename which violates the kebab-case
naming convention. The structure check should flag this. It
contains enough content to avoid being flagged as thin but the
filename itself is the issue being tested here.
""",
    )
    return tmp_path


# ---- 1. Healthy wiki exits 0, no errors ----


def test_healthy_wiki_exits_zero(runner: CliRunner, healthy_wiki_dir: Path):
    result = runner.invoke(main, [str(healthy_wiki_dir)])
    assert result.exit_code == 0
    # Should not contain ERROR-level issues
    assert (
        "ERROR" not in (result.output or "").upper().split("SEVERITY")[0]
        or "error" not in result.output.lower()
    )


# ---- 2. Unhealthy wiki exits 0 (not CI), shows issues ----


def test_unhealthy_wiki_exits_zero_without_ci(runner: CliRunner, unhealthy_wiki_dir: Path):
    result = runner.invoke(main, [str(unhealthy_wiki_dir)])
    assert result.exit_code == 0
    # Should show some issues in output
    output_lower = result.output.lower()
    assert "broken" in output_lower or "error" in output_lower or "warning" in output_lower


# ---- 3. --ci on unhealthy wiki exits 1 ----


def test_ci_unhealthy_exits_one(runner: CliRunner, unhealthy_wiki_dir: Path):
    result = runner.invoke(main, [str(unhealthy_wiki_dir), "--ci"])
    assert result.exit_code == 1


# ---- 4. --ci on healthy wiki exits 0 ----


def test_ci_healthy_exits_zero(runner: CliRunner, healthy_wiki_dir: Path):
    result = runner.invoke(main, [str(healthy_wiki_dir), "--ci"])
    assert result.exit_code == 0


# ---- 5. --format json outputs valid JSON ----


def test_format_json(runner: CliRunner, unhealthy_wiki_dir: Path):
    result = runner.invoke(main, [str(unhealthy_wiki_dir), "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "issues" in data
    assert "health_score" in data
    assert "summary" in data
    assert isinstance(data["issues"], list)
    assert len(data["issues"]) > 0


# ---- 6. --format markdown outputs markdown ----


def test_format_markdown(runner: CliRunner, unhealthy_wiki_dir: Path):
    result = runner.invoke(main, [str(unhealthy_wiki_dir), "--format", "markdown"])
    assert result.exit_code == 0
    assert "# Knowledge Base Health Report" in result.output
    assert "|" in result.output  # markdown table


# ---- 7. --severity error only shows errors ----


def test_severity_error_filter(runner: CliRunner, unhealthy_wiki_dir: Path):
    result = runner.invoke(
        main,
        [str(unhealthy_wiki_dir), "--format", "json", "--severity", "error"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    for issue in data["issues"]:
        assert issue["severity"] == "error"
    # There should be at least one error (broken links)
    assert len(data["issues"]) > 0


# ---- 8. --check links only runs links check ----


def test_single_check(runner: CliRunner, unhealthy_wiki_dir: Path):
    result = runner.invoke(main, [str(unhealthy_wiki_dir), "--format", "json", "--check", "links"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    checks_used = {issue["check"] for issue in data["issues"]}
    # Only links check should appear
    assert checks_used <= {"links"}


# ---- 9. --check links,frontmatter runs multiple checks ----


def test_multiple_checks(runner: CliRunner, unhealthy_wiki_dir: Path):
    result = runner.invoke(
        main,
        [str(unhealthy_wiki_dir), "--format", "json", "--check", "links,frontmatter"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    checks_used = {issue["check"] for issue in data["issues"]}
    # Should only contain links and/or frontmatter
    assert checks_used <= {"links", "frontmatter"}
    # Should have at least issues from both checks
    assert "links" in checks_used
    assert "frontmatter" in checks_used


# ---- 10. --list-checks shows available checks ----


def test_list_checks(runner: CliRunner):
    result = runner.invoke(main, ["--list-checks"])
    assert result.exit_code == 0
    output = result.output
    assert "links" in output
    assert "frontmatter" in output
    assert "orphans" in output
    assert "structure" in output
    assert "content" in output
    assert "index" in output
    assert "consistency" in output


# ---- 11. nonexistent path handled gracefully ----


def test_nonexistent_path(runner: CliRunner):
    result = runner.invoke(main, ["/tmp/this-path-absolutely-does-not-exist-kb-lint"])
    # Click should catch the invalid path and report an error
    assert result.exit_code != 0
    assert (
        "does not exist" in result.output.lower()
        or "error" in result.output.lower()
        or "no such" in result.output.lower()
    )


# ---- 12. --fix applies fixes and re-reports ----


def test_fix_applies_and_reruns(runner: CliRunner, unhealthy_wiki_dir: Path):
    # First run without fix to capture baseline issues
    baseline = runner.invoke(main, [str(unhealthy_wiki_dir), "--format", "json"])
    baseline_data = json.loads(baseline.output)
    baseline_count = len(baseline_data["issues"])

    # Run with --fix
    result = runner.invoke(main, [str(unhealthy_wiki_dir), "--fix"])
    assert result.exit_code == 0
    output_lower = result.output.lower()
    # Should mention fixes or indicate no fixable issues
    assert "fix" in output_lower

    # Run again without fix to see if issues were reduced
    after = runner.invoke(main, [str(unhealthy_wiki_dir), "--format", "json"])
    after_data = json.loads(after.output)
    after_count = len(after_data["issues"])
    # After fixing, issue count should be <= baseline
    assert after_count <= baseline_count
