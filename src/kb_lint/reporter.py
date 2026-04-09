"""Output formatters: terminal (Rich), markdown, and JSON."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from rich.console import Console
from rich.table import Table

from kb_lint.models import Article, Issue, Severity


def _health_score(issues: list[Issue]) -> int:
    """Compute a health score from 0-100 based on issues found."""
    if not issues:
        return 100
    penalty = 0
    for issue in issues:
        if issue.severity == Severity.ERROR:
            penalty += 10
        elif issue.severity == Severity.WARNING:
            penalty += 3
        else:
            penalty += 1
    return max(0, 100 - penalty)


def _count_total_links(articles: list[Article]) -> int:
    """Count total wiki-links across all articles."""
    return sum(len(a.wiki_links) for a in articles)


def _severity_icon(severity: Severity) -> str:
    if severity == Severity.ERROR:
        return "[red]E[/red]"
    elif severity == Severity.WARNING:
        return "[yellow]W[/yellow]"
    return "[blue]I[/blue]"


def _severity_plain(severity: Severity) -> str:
    return severity.value.upper()


def format_terminal(
    issues: list[Issue],
    articles: list[Article],
    wiki_path: Path,
    is_report: bool = False,
) -> None:
    """Print a rich terminal report."""
    console = Console()

    errors = sum(1 for i in issues if i.severity == Severity.ERROR)
    warnings = sum(1 for i in issues if i.severity == Severity.WARNING)
    infos = sum(1 for i in issues if i.severity == Severity.INFO)
    total_links = _count_total_links(articles)

    if is_report:
        console.print()
        console.rule("[bold]Knowledge Base Health Report[/bold]")
        console.print(f"  [dim]Path:[/dim]     {wiki_path}")
        console.print(f"  [dim]Articles:[/dim] {len(articles)}")
        console.print(f"  [dim]Links:[/dim]    {total_links}")
        console.print()

    # Summary line
    parts = []
    if errors:
        parts.append(f"[red bold]{errors} error{'s' if errors != 1 else ''}[/red bold]")
    if warnings:
        parts.append(f"[yellow]{warnings} warning{'s' if warnings != 1 else ''}[/yellow]")
    if infos:
        parts.append(f"[blue]{infos} info[/blue]")

    if not issues:
        console.print("[green bold]No issues found. Knowledge base is healthy![/green bold]")
    else:
        console.print("  ".join(parts))
        console.print()

        # Group by file
        by_file: dict[Path, list[Issue]] = defaultdict(list)
        for issue in issues:
            by_file[issue.file].append(issue)

        table = Table(show_header=True, header_style="bold", expand=True)
        table.add_column("Sev", width=3)
        table.add_column("File", style="cyan", ratio=2, overflow="fold")
        table.add_column("Line", width=5, justify="right")
        table.add_column("Check", style="dim", width=12)
        table.add_column("Message", ratio=4, overflow="fold")

        for file_path in sorted(by_file):
            file_issues = sorted(by_file[file_path], key=lambda i: i.line or 0)
            for issue in file_issues:
                table.add_row(
                    _severity_icon(issue.severity),
                    str(file_path),
                    str(issue.line) if issue.line else "-",
                    issue.check,
                    issue.message,
                )

        console.print(table)

        # Suggestions
        fixable = [i for i in issues if i.fixable]
        if fixable:
            n = len(fixable)
            s = "s" if n != 1 else ""
            console.print(f"\n[dim]{n} issue{s} can be auto-fixed with --fix[/dim]")

    if is_report:
        score = _health_score(issues)
        color = "green" if score >= 80 else "yellow" if score >= 50 else "red"
        console.print(f"\n[{color} bold]Health Score: {score}/100[/{color} bold]")
        console.print()


def format_markdown(
    issues: list[Issue],
    articles: list[Article],
    wiki_path: Path,
) -> str:
    """Generate a markdown report."""
    lines: list[str] = []
    errors = sum(1 for i in issues if i.severity == Severity.ERROR)
    warnings = sum(1 for i in issues if i.severity == Severity.WARNING)
    infos = sum(1 for i in issues if i.severity == Severity.INFO)
    total_links = _count_total_links(articles)
    score = _health_score(issues)

    lines.append("# Knowledge Base Health Report")
    lines.append("")
    lines.append(f"- **Path**: `{wiki_path}`")
    lines.append(f"- **Articles**: {len(articles)}")
    lines.append(f"- **Links**: {total_links}")
    lines.append(f"- **Health Score**: {score}/100")
    lines.append("")
    lines.append(f"**{errors}** errors, **{warnings}** warnings, **{infos}** info")
    lines.append("")

    if not issues:
        lines.append("No issues found. Knowledge base is healthy!")
        return "\n".join(lines)

    # Group by file
    by_file: dict[Path, list[Issue]] = defaultdict(list)
    for issue in issues:
        by_file[issue.file].append(issue)

    lines.append("## Issues")
    lines.append("")
    lines.append("| Severity | File | Line | Check | Message |")
    lines.append("|----------|------|------|-------|---------|")

    for file_path in sorted(by_file):
        file_issues = sorted(by_file[file_path], key=lambda i: i.line or 0)
        for issue in file_issues:
            sev = _severity_plain(issue.severity)
            line_str = str(issue.line) if issue.line else "-"
            # Escape pipe characters to prevent breaking markdown tables
            safe_path = str(file_path).replace("|", "\\|")
            safe_message = issue.message.replace("|", "\\|")
            safe_check = issue.check.replace("|", "\\|")
            lines.append(f"| {sev} | `{safe_path}` | {line_str} | {safe_check} | {safe_message} |")

    lines.append("")
    return "\n".join(lines)


def format_json(
    issues: list[Issue],
    articles: list[Article],
    wiki_path: Path,
) -> str:
    """Generate a JSON report."""
    errors = sum(1 for i in issues if i.severity == Severity.ERROR)
    warnings = sum(1 for i in issues if i.severity == Severity.WARNING)
    infos = sum(1 for i in issues if i.severity == Severity.INFO)

    data = {
        "path": str(wiki_path),
        "articles": len(articles),
        "links": _count_total_links(articles),
        "health_score": _health_score(issues),
        "summary": {
            "errors": errors,
            "warnings": warnings,
            "info": infos,
        },
        "issues": [
            {
                "check": issue.check,
                "severity": issue.severity.value,
                "file": str(issue.file),
                "line": issue.line,
                "message": issue.message,
                "suggestion": issue.suggestion,
                "fixable": issue.fixable,
            }
            for issue in sorted(issues, key=lambda i: (str(i.file), i.line or 0))
        ],
    }

    return json.dumps(data, indent=2, ensure_ascii=False)


__all__ = ["format_terminal", "format_markdown", "format_json"]
