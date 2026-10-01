"""Render a run as Rich tables of one shared width and first column."""

from __future__ import annotations

import shutil
import sys

from colored import fore, style, stylize
from rich.cells import cell_len
from rich.console import Console
from rich.table import Table
from rich.text import Text

from lupaxa.github_token_validator.probes import ProbeRow, RunReport

_RESULT_COLORS = {
    "granted": "green",
    "denied": "red",
    "not applicable": "yellow",
    "not checked": "dark_gray",
}


def render_report(report: RunReport, console: Console | None = None) -> None:
    """Print the tables selected by the report flags."""
    output = _default_console() if console is None else console
    first_width = _first_column_width(report)
    if report.show_summary:
        _summary(output, report, first_width)
    if report.show_scopes:
        _scopes(output, report, first_width)
    if report.show_account:
        _account(output, report, first_width)
    if report.show_target:
        _targets(output, report, first_width)
    if report.error is not None:
        output.print(_paint(report.error, "red", bold=True))


def _default_console() -> Console:
    """Use a wide layout when stdout is not an interactive terminal."""
    if sys.stdout.isatty():
        return Console()
    columns = shutil.get_terminal_size(fallback=(200, 24)).columns
    return Console(width=max(200, columns), _environ={})


def _summary(console: Console, report: RunReport, first_width: int) -> None:
    table = _table(console, "Summary")
    _columns(table, ("Field", "Value"), first_width)
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
        table.add_row(_plain(field), _plain(value))
    console.print(table)


def _scopes(console: Console, report: RunReport, first_width: int) -> None:
    table = _table(console, "Scopes")
    _columns(table, ("Scope", "Allows"), first_width)
    for scope, allows in report.scope_rows:
        table.add_row(_plain(scope), _plain(allows))
    console.print(table)


def _account(console: Console, report: RunReport, first_width: int) -> None:
    table = _table(console, "Account permissions")
    endpoint_width = _endpoint_width(report.account_rows)
    _permission_columns(
        table,
        ("Check", "Endpoint", "Result", "Meaning"),
        first_width,
        endpoint_width,
    )
    for row in report.account_rows:
        _add_permission(table, row, include_target=False)
    console.print(table)


def _targets(console: Console, report: RunReport, first_width: int) -> None:
    table = _table(console, "Target permissions")
    endpoint_width = _endpoint_width(report.target_rows)
    _permission_columns(
        table,
        ("Target", "Check", "Endpoint", "Result", "Meaning"),
        first_width,
        endpoint_width,
    )
    for row in report.target_rows:
        _add_permission(table, row, include_target=True)
    console.print(table)


def _first_column_width(report: RunReport) -> int:
    """Return one content width for the first column of every visible table."""
    cells = _first_column_cells(report)
    if not cells:
        return 1
    return max(cell_len(cell) for cell in cells)


def _first_column_cells(report: RunReport) -> tuple[str, ...]:
    cells: list[str] = []
    if report.show_summary:
        cells.extend(
            (
                "Field",
                "Token kind",
                "Login",
                "Scopes",
                "Rate limit",
                "Used",
                "Remaining",
                "Reset",
            )
        )
    if report.show_scopes:
        cells.append("Scope")
        cells.extend(scope for scope, _allows in report.scope_rows)
    if report.show_account:
        cells.append("Check")
        cells.extend(row.check for row in report.account_rows)
    if report.show_target:
        cells.append("Target")
        cells.extend(row.target for row in report.target_rows)
    return tuple(cells)


def _columns(table: Table, headings: tuple[str, ...], first_width: int) -> None:
    """Pin the first column and let the remaining columns share the rest."""
    table.add_column(
        _heading(headings[0]),
        width=first_width,
        no_wrap=True,
        overflow="ellipsis",
    )
    for heading in headings[1:]:
        table.add_column(_heading(heading), ratio=1)


def _endpoint_width(rows: tuple[ProbeRow, ...]) -> int:
    if not rows:
        return 1
    return max(cell_len(row.endpoint) for row in rows)


def _permission_columns(
    table: Table,
    headings: tuple[str, ...],
    first_width: int,
    endpoint_width: int,
) -> None:
    """Like ``_columns``, but keep probe endpoints on one line when possible."""
    table.add_column(
        _heading(headings[0]),
        width=first_width,
        no_wrap=True,
        overflow="ellipsis",
    )
    for heading in headings[1:]:
        if heading == "Endpoint":
            table.add_column(
                _heading(heading),
                min_width=endpoint_width,
                no_wrap=True,
                ratio=1,
            )
        else:
            table.add_column(_heading(heading), ratio=1)


def _table(console: Console, title: str) -> Table:
    """Build a table that fills the console width."""
    return Table(
        title=_paint(title, "cyan", bold=True),
        width=console.width,
        expand=True,
        header_style="none",
    )


def _add_permission(table: Table, row: ProbeRow, *, include_target: bool) -> None:
    cells: list[Text] = [
        _plain(row.check),
        _plain(row.endpoint),
        _result(row.result),
        _plain(row.meaning),
    ]
    if include_target:
        cells.insert(0, _plain(row.target))
    table.add_row(*cells)


def _heading(text: str) -> Text:
    return _paint(text, "light_blue", bold=True)


def _plain(text: str) -> Text:
    return Text(text)


def _result(result: str) -> Text:
    color = _RESULT_COLORS.get(result)
    if color is None and result.startswith("error"):
        color = "light_red"
    if color is None:
        return _plain(result)
    return _paint(result, color, bold=True)


def _paint(text: str, color: str, *, bold: bool = False) -> Text:
    """Color ``text`` with the colored library and hand Rich a styled span."""
    formatting = f"{style('bold')}{fore(color)}" if bold else str(fore(color))
    return Text.from_ansi(str(stylize(text, formatting)))
