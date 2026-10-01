"""Rich output contains only the report fields."""

from __future__ import annotations

from dataclasses import replace
from io import StringIO

from colored import set_tty_aware
import pytest
from rich.console import Console

from lupaxa.github_token_validator.probes import ProbeRow, RunReport
from lupaxa.github_token_validator.report import render_report


def _report() -> RunReport:
    return RunReport(
        kind_label="Classic personal access token",
        login="octocat",
        scopes_raw="repo",
        scope_rows=(
            (
                "repo",
                "Full read and write access to public and private repository code",
            ),
        ),
        rate_limit="5000",
        rate_used="7",
        rate_remaining="4993",
        rate_reset="2023-11-14 22:13:20",
        account_rows=(
            ProbeRow(
                "",
                "Repository list",
                "GET /user/repos?per_page=1",
                "granted",
                (
                    "Read whether the repository list is allowed. "
                    "Do not print repository names"
                ),
            ),
        ),
        target_rows=(
            ProbeRow(
                "repository",
                "Contents",
                "GET /repos/{owner}/{repo}/contents",
                "not checked",
                "Read repository contents. Do not print paths",
            ),
        ),
        error=None,
        exit_code=0,
        show_summary=True,
        show_scopes=True,
        show_account=True,
        show_target=True,
    )


def _render(report: RunReport) -> str:
    buffer = StringIO()
    console = Console(file=buffer, width=160, force_terminal=False, color_system=None)
    render_report(report, console)
    return buffer.getvalue()


def test_render_includes_the_four_tables_and_not_a_body_sentinel() -> None:
    text = _render(_report())
    assert "Summary" in text
    assert "Scopes" in text
    assert "Account permissions" in text
    assert "Target permissions" in text
    assert "octocat" in text
    assert "not checked" in text
    assert "leaked-repo-path" not in text


def test_table_headers_are_capitalised() -> None:
    text = _render(_report())
    headers = "\n".join(line for line in text.splitlines() if "┃" in line)
    for heading in (
        "Field",
        "Value",
        "Scope",
        "Allows",
        "Check",
        "Endpoint",
        "Result",
        "Meaning",
        "Target",
    ):
        assert heading in headers


def test_tables_use_the_same_width() -> None:
    text = _render(_report())
    borders = [
        line for line in text.splitlines() if line.startswith(("┏", "┌", "╰", "└", "╭"))
    ]
    assert len(borders) >= 3
    assert len({len(line) for line in borders}) == 1


def test_first_columns_share_one_width() -> None:
    text = _render(_report())
    positions = [
        position
        for line in text.splitlines()
        if (position := _divider_after_first_column(line)) is not None
    ]
    assert len(positions) >= 4
    assert len(set(positions)) == 1


def _divider_after_first_column(line: str) -> int | None:
    bars = [index for index, char in enumerate(line) if char in "┃│"]
    if len(bars) < 2:
        return None
    return bars[1]


def test_results_and_titles_are_colored(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    set_tty_aware(False)
    buffer = StringIO()
    console = Console(
        file=buffer,
        width=100,
        force_terminal=True,
        color_system="standard",
        no_color=False,
    )
    try:
        render_report(_report(), console)
    finally:
        set_tty_aware(True)
    text = buffer.getvalue()
    colored_rows = [line for line in text.splitlines() if "granted" in line]
    assert colored_rows
    assert "\x1b[" in colored_rows[0]


def test_markup_in_cells_is_shown_as_text() -> None:
    text = _render(replace(_report(), login="[bold]octocat[/bold]"))
    assert "[bold]octocat[/bold]" in text


def test_hidden_tables_print_only_the_error() -> None:
    source = _report()
    hidden = RunReport(
        kind_label=source.kind_label,
        login=source.login,
        scopes_raw=source.scopes_raw,
        scope_rows=source.scope_rows,
        rate_limit=source.rate_limit,
        rate_used=source.rate_used,
        rate_remaining=source.rate_remaining,
        rate_reset=source.rate_reset,
        account_rows=source.account_rows,
        target_rows=source.target_rows,
        error="GitHub rejected the token (HTTP 401).",
        exit_code=1,
        show_summary=False,
        show_scopes=False,
        show_account=False,
        show_target=False,
    )
    text = _render(hidden)
    assert "Summary" not in text
    assert text.strip() == "GitHub rejected the token (HTTP 401)."
