"""Render a run as Rich tables."""

from __future__ import annotations

from rich.console import Console
from rich.markup import escape
from rich.table import Table

from lupaxa.github_token_validator.probes import ProbeRow, RunReport


def render_report(report: RunReport, console: Console | None = None) -> None:
    """Print the tables selected by the report flags."""
    output = Console() if console is None else console
    if report.show_summary:
        _summary(output, report)
    if report.show_scopes:
        _scopes(output, report)
    if report.show_account:
        _account(output, report)
    if report.show_target:
        _targets(output, report)
    if report.error is not None:
        output.print(escape(report.error))


def _summary(console: Console, report: RunReport) -> None:
    table = Table(title="Summary")
    table.add_column("Field")
    table.add_column("Value")
    rows = (
        ("Token kind", report.kind_label),
        ("Login", report.login),
        ("Scopes", report.scopes_raw),
        ("Rate limit", report.rate_limit),
        ("Used", report.rate_used),
        ("Remaining", report.rate_remaining),
        ("Reset", report.rate_reset),
    )
    for field, value in rows:
        table.add_row(escape(field), escape(value))
    console.print(table)


def _scopes(console: Console, report: RunReport) -> None:
    table = Table(title="Scopes")
    table.add_column("scope")
    table.add_column("allows")
    for scope, allows in report.scope_rows:
        table.add_row(escape(scope), escape(allows))
    console.print(table)


def _account(console: Console, report: RunReport) -> None:
    table = Table(title="Account permissions")
    for column in ("check", "endpoint", "result", "meaning"):
        table.add_column(column)
    for row in report.account_rows:
        _add_permission(table, row, include_target=False)
    console.print(table)


def _targets(console: Console, report: RunReport) -> None:
    table = Table(title="Target permissions")
    for column in ("target", "check", "endpoint", "result", "meaning"):
        table.add_column(column)
    for row in report.target_rows:
        _add_permission(table, row, include_target=True)
    console.print(table)


def _add_permission(table: Table, row: ProbeRow, *, include_target: bool) -> None:
    cells = [row.check, row.endpoint, row.result, row.meaning]
    if include_target:
        cells.insert(0, row.target)
    table.add_row(*(escape(cell) for cell in cells))
