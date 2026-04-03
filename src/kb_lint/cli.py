"""Click CLI for kb-lint."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console

from kb_lint import __version__
from kb_lint.checks import CHECK_DESCRIPTIONS, run_checks
from kb_lint.config import Config
from kb_lint.fixer import apply_fixes
from kb_lint.models import Severity
from kb_lint.reporter import format_json, format_markdown, format_terminal
from kb_lint.scanner import scan

_SEVERITY_MAP = {
    "error": Severity.ERROR,
    "warning": Severity.WARNING,
    "info": Severity.INFO,
}


@click.command()
@click.argument(
    "path",
    default=".",
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
)
@click.option(
    "--format", "fmt",
    type=click.Choice(["terminal", "markdown", "json"]),
    default="terminal",
    help="Output format.",
)
@click.option(
    "--severity",
    type=click.Choice(["error", "warning", "info"]),
    default=None,
    help="Minimum severity to report.",
)
@click.option("--fix", is_flag=True, help="Auto-fix simple issues.")
@click.option(
    "--check", "checks_str",
    default=None,
    help="Comma-separated list of checks to run.",
)
@click.option("--list-checks", is_flag=True, help="Show available checks.")
@click.option("--report", is_flag=True, help="Generate a health report.")
@click.option("--ci", is_flag=True, help="CI mode: exit 1 if errors found.")
@click.version_option(version=__version__, prog_name="kb-lint")
def main(
    path: str,
    fmt: str,
    severity: str | None,
    fix: bool,
    checks_str: str | None,
    list_checks: bool,
    report: bool,
    ci: bool,
) -> None:
    """Lint a knowledge base directory for structural and content issues."""
    console = Console()

    if list_checks:
        console.print("[bold]Available checks:[/bold]\n")
        for name, desc in CHECK_DESCRIPTIONS.items():
            console.print(f"  [cyan]{name:15s}[/cyan] {desc}")
        console.print()
        return

    wiki_path = Path(path)

    # Build config overrides from CLI
    overrides: dict = {}
    if severity:
        overrides["severity_threshold"] = severity
    if checks_str:
        overrides["checks"] = [c.strip() for c in checks_str.split(",")]

    config = Config.load(wiki_path, overrides)

    # Parse selected checks
    selected = [c.strip() for c in checks_str.split(",")] if checks_str else None

    # Scan
    articles = scan(wiki_path, config)

    if not articles:
        console.print("[yellow]No markdown files found in the specified path.[/yellow]")
        return

    # Run checks
    issues = run_checks(articles, config, selected)

    # Filter by severity
    threshold = _SEVERITY_MAP.get(config.severity_threshold, Severity.INFO)
    issues = [i for i in issues if i.severity >= threshold]

    # Auto-fix
    if fix:
        fix_results = apply_fixes(issues, articles, wiki_path, config)
        if fix_results:
            console.print("[green bold]Fixes applied:[/green bold]")
            for desc in fix_results:
                console.print(f"  [green]>[/green] {desc}")
            console.print()
            # Re-scan and re-check after fixes
            articles = scan(wiki_path, config)
            issues = run_checks(articles, config, selected)
            issues = [i for i in issues if i.severity >= threshold]
        else:
            console.print("[dim]No auto-fixable issues found.[/dim]\n")

    # Output
    if fmt == "terminal":
        format_terminal(issues, articles, wiki_path, is_report=report)
    elif fmt == "markdown":
        output = format_markdown(issues, articles, wiki_path)
        click.echo(output)
    elif fmt == "json":
        output = format_json(issues, articles, wiki_path)
        click.echo(output)

    # CI mode exit code
    if ci:
        error_count = sum(1 for i in issues if i.severity == Severity.ERROR)
        if error_count > 0:
            sys.exit(1)


__all__ = ["main"]
