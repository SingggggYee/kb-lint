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
@click.option("--dry-run", is_flag=True, help="Preview fixes without writing (use with --fix).")
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
    dry_run: bool,
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

    selected: list[str] | None = None
    if checks_str:
        selected = [c.strip() for c in checks_str.split(",")]
        overrides["checks"] = selected

    config = Config.load(wiki_path, overrides)

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

    # Validate --dry-run usage
    if dry_run and not fix:
        console.print(
            "[red]Error: --dry-run requires --fix. "
            "Use '--fix --dry-run' to preview changes.[/red]"
        )
        sys.exit(2)

    # Auto-fix
    if fix:
        fix_results, modified_files = apply_fixes(issues, articles, wiki_path, config, dry_run=dry_run)
        if fix_results:
            if dry_run:
                console.print("[yellow bold]Dry run — no files modified:[/yellow bold]")
                for desc in fix_results:
                    console.print(f"  [yellow]~[/yellow] {desc}")
                console.print()
            else:
                console.print("[green bold]Fixes applied:[/green bold]")
                for desc in fix_results:
                    console.print(f"  [green]>[/green] {desc}")
                console.print()
                # Re-scan only modified files, reusing cached articles for the rest
                articles = scan(
                    wiki_path, config,
                    changed_files=modified_files,
                    previous_articles=articles,
                )
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
