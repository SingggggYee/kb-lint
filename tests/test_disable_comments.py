"""Tests for inline disable comment support."""

from __future__ import annotations

from pathlib import Path

from kb_lint.checks import run_checks
from kb_lint.config import Config
from kb_lint.scanner import scan


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _make_config() -> Config:
    return Config()


# ---------------------------------------------------------------------------
# Range disable: suppresses issues between disable/enable
# ---------------------------------------------------------------------------


def test_range_disable_suppresses_issues_in_range(tmp_path: Path):
    """Issues inside a disable/enable range are suppressed."""
    _write(
        tmp_path / "_index.md",
        """\
---
title: "Index"
---

# Index

- [[article-a]]
""",
    )
    _write(
        tmp_path / "article-a.md",
        """\
---
title: "Article A"
tags: [test]
created: 2024-01-15
confidence: high
sources: ["https://example.com"]
related: []
---

# Article A

Some intro text here to make it long enough to not be thin.
We need enough words so the content check does not flag this.
More words to reach the minimum threshold for the article.
Even more filler content to make absolutely sure we pass.
This article covers a lot of ground and is quite comprehensive.
Additional context and detail to flesh out the article body.

<!-- kb-lint-disable links -->
See [[broken-link-1]] for details.
See [[broken-link-2]] for more.
<!-- kb-lint-enable links -->
""",
    )

    config = _make_config()
    articles = scan(tmp_path, config)
    issues = run_checks(articles, config, selected_checks=["links"])

    # Both broken links should be suppressed
    link_msgs = [i.message for i in issues]
    assert not any("broken-link-1" in m for m in link_msgs)
    assert not any("broken-link-2" in m for m in link_msgs)


# ---------------------------------------------------------------------------
# Enable re-enables after disable
# ---------------------------------------------------------------------------


def test_enable_re_enables_after_disable(tmp_path: Path):
    """Issues after an enable comment are NOT suppressed."""
    _write(
        tmp_path / "_index.md",
        """\
---
title: "Index"
---

# Index

- [[article-b]]
""",
    )
    _write(
        tmp_path / "article-b.md",
        """\
---
title: "Article B"
tags: [test]
created: 2024-01-15
confidence: high
sources: ["https://example.com"]
related: []
---

# Article B

Some intro text here to make it long enough to not be thin.
We need enough words so the content check does not flag this.
More words to reach the minimum threshold for the article.
Even more filler content to make absolutely sure we pass.
This article covers a lot of ground and is quite comprehensive.
Additional context and detail to flesh out the article body.

<!-- kb-lint-disable links -->
See [[hidden-link]] for details.
<!-- kb-lint-enable links -->

See [[visible-link]] for more.
""",
    )

    config = _make_config()
    articles = scan(tmp_path, config)
    issues = run_checks(articles, config, selected_checks=["links"])

    link_msgs = [i.message for i in issues]
    assert not any("hidden-link" in m for m in link_msgs)
    assert any("visible-link" in m for m in link_msgs)


# ---------------------------------------------------------------------------
# disable-next-line only suppresses one line
# ---------------------------------------------------------------------------


def test_disable_next_line_only_suppresses_one_line(tmp_path: Path):
    """disable-next-line only suppresses the immediately following line."""
    _write(
        tmp_path / "_index.md",
        """\
---
title: "Index"
---

# Index

- [[article-c]]
""",
    )
    _write(
        tmp_path / "article-c.md",
        """\
---
title: "Article C"
tags: [test]
created: 2024-01-15
confidence: high
sources: ["https://example.com"]
related: []
---

# Article C

Some intro text here to make it long enough to not be thin.
We need enough words so the content check does not flag this.
More words to reach the minimum threshold for the article.
Even more filler content to make absolutely sure we pass.
This article covers a lot of ground and is quite comprehensive.
Additional context and detail to flesh out the article body.

<!-- kb-lint-disable-next-line links -->
See [[hidden-link]] for details.
See [[visible-link]] for more.
""",
    )

    config = _make_config()
    articles = scan(tmp_path, config)
    issues = run_checks(articles, config, selected_checks=["links"])

    link_msgs = [i.message for i in issues]
    assert not any("hidden-link" in m for m in link_msgs)
    assert any("visible-link" in m for m in link_msgs)


# ---------------------------------------------------------------------------
# disable-file suppresses entire file
# ---------------------------------------------------------------------------


def test_disable_file_suppresses_entire_file(tmp_path: Path):
    """disable-file suppresses all issues of that check in the file."""
    _write(
        tmp_path / "_index.md",
        """\
---
title: "Index"
---

# Index

- [[article-d]]
""",
    )
    _write(
        tmp_path / "article-d.md",
        """\
---
title: "Article D"
tags: [test]
created: 2024-01-15
confidence: high
sources: ["https://example.com"]
related: []
---

<!-- kb-lint-disable-file links -->

# Article D

Some intro text here to make it long enough to not be thin.
We need enough words so the content check does not flag this.
More words to reach the minimum threshold for the article.
Even more filler content to make absolutely sure we pass.
This article covers a lot of ground and is quite comprehensive.
Additional context and detail to flesh out the article body.

See [[broken-link-1]] for details.
See [[broken-link-2]] for more.
See [[broken-link-3]] at the end.
""",
    )

    config = _make_config()
    articles = scan(tmp_path, config)
    issues = run_checks(articles, config, selected_checks=["links"])

    # All broken links in this file should be suppressed
    file_issues = [i for i in issues if "article-d" in str(i.file)]
    assert len(file_issues) == 0


# ---------------------------------------------------------------------------
# Disable all checks (no check name)
# ---------------------------------------------------------------------------


def test_disable_all_checks_no_name(tmp_path: Path):
    """Disable without a check name suppresses ALL checks."""
    _write(
        tmp_path / "_index.md",
        """\
---
title: "Index"
---

# Index

- [[article-e]]
""",
    )
    _write(
        tmp_path / "article-e.md",
        """\
---
title: "Article E"
tags: [test]
created: 2024-01-15
confidence: high
sources: ["https://example.com"]
related: []
---

# Article E

Some intro text here to make it long enough to not be thin.
We need enough words so the content check does not flag this.
More words to reach the minimum threshold for the article.
Even more filler content to make absolutely sure we pass.
This article covers a lot of ground and is quite comprehensive.
Additional context and detail to flesh out the article body.

<!-- kb-lint-disable -->
See [[broken-link-all]] for details.
<!-- kb-lint-enable -->
""",
    )

    config = _make_config()
    articles = scan(tmp_path, config)
    issues = run_checks(articles, config, selected_checks=["links"])

    link_msgs = [i.message for i in issues]
    assert not any("broken-link-all" in m for m in link_msgs)


def test_disable_file_all_checks(tmp_path: Path):
    """disable-file without a check name suppresses ALL checks for the file."""
    _write(
        tmp_path / "_index.md",
        """\
---
title: "Index"
---

# Index

- [[article-f]]
""",
    )
    _write(
        tmp_path / "article-f.md",
        """\
---
title: "Article F"
tags: [test]
created: 2024-01-15
confidence: high
sources: ["https://example.com"]
related: []
---

<!-- kb-lint-disable-file -->

# Article F

Short.
""",
    )

    config = _make_config()
    articles = scan(tmp_path, config)
    issues = run_checks(articles, config)

    # No issues at all for article-f
    file_issues = [i for i in issues if "article-f" in str(i.file)]
    assert len(file_issues) == 0


# ---------------------------------------------------------------------------
# Unknown check name is ignored (no error)
# ---------------------------------------------------------------------------


def test_unknown_check_name_no_error(tmp_path: Path):
    """An unknown check name in a disable comment causes no error."""
    _write(
        tmp_path / "_index.md",
        """\
---
title: "Index"
---

# Index

- [[article-g]]
""",
    )
    _write(
        tmp_path / "article-g.md",
        """\
---
title: "Article G"
tags: [test]
created: 2024-01-15
confidence: high
sources: ["https://example.com"]
related: []
---

# Article G

Some intro text here to make it long enough to not be thin.
We need enough words so the content check does not flag this.
More words to reach the minimum threshold for the article.
Even more filler content to make absolutely sure we pass.
This article covers a lot of ground and is quite comprehensive.
Additional context and detail to flesh out the article body.

<!-- kb-lint-disable nonexistent-check -->
See [[still-broken]] for details.
<!-- kb-lint-enable nonexistent-check -->
""",
    )

    config = _make_config()
    articles = scan(tmp_path, config)
    # Should not raise any exception
    issues = run_checks(articles, config, selected_checks=["links"])

    # The broken link is NOT suppressed because the disable targets a different check
    link_msgs = [i.message for i in issues]
    assert any("still-broken" in m for m in link_msgs)


def test_disable_next_line_all_checks(tmp_path: Path):
    """disable-next-line without a check name suppresses ALL checks for that line."""
    _write(
        tmp_path / "_index.md",
        """\
---
title: "Index"
---

# Index

- [[article-h]]
""",
    )
    _write(
        tmp_path / "article-h.md",
        """\
---
title: "Article H"
tags: [test]
created: 2024-01-15
confidence: high
sources: ["https://example.com"]
related: []
---

# Article H

Some intro text here to make it long enough to not be thin.
We need enough words so the content check does not flag this.
More words to reach the minimum threshold for the article.
Even more filler content to make absolutely sure we pass.
This article covers a lot of ground and is quite comprehensive.
Additional context and detail to flesh out the article body.

<!-- kb-lint-disable-next-line -->
See [[broken-link-h]] for details.
""",
    )

    config = _make_config()
    articles = scan(tmp_path, config)
    issues = run_checks(articles, config, selected_checks=["links"])

    link_msgs = [i.message for i in issues]
    assert not any("broken-link-h" in m for m in link_msgs)
