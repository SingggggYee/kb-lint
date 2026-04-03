"""Shared fixtures for kb-lint tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from kb_lint.config import Config
from kb_lint.scanner import scan


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def default_config() -> Config:
    """Return a default Config instance."""
    return Config()


@pytest.fixture
def healthy_wiki(tmp_path: Path) -> Path:
    """Create a small healthy wiki for testing."""
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
def unhealthy_wiki(tmp_path: Path) -> Path:
    """Create a wiki with various issues for testing."""
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
    _write(
        tmp_path / "concepts" / "placeholder-article.md",
        """\
---
title: "Placeholder Article"
tags: [test]
created: 2024-01-10
confidence: medium
---

# Placeholder Article

This article has a template placeholder below that should be detected by the content check.

## Details

{{PLACEHOLDER_CONTENT}}

More text after the placeholder to ensure the article is long
enough to not be flagged as thin. We need sufficient words here
to pass the minimum threshold.
""",
    )
    return tmp_path


@pytest.fixture
def healthy_articles(healthy_wiki: Path, default_config: Config):
    return scan(healthy_wiki, default_config)


@pytest.fixture
def unhealthy_articles(unhealthy_wiki: Path, default_config: Config):
    return scan(unhealthy_wiki, default_config)
