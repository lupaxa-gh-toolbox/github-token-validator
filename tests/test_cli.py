"""CLI exits and output. The factory replaces the network."""

from __future__ import annotations

import pytest

from lupaxa.github_token_validator.cli import main
from lupaxa.github_token_validator.client import GitHubResponse, GitHubUnauthorizedError
from lupaxa.github_token_validator.constants import PROGRAM_VERSION_STRING
from lupaxa.github_token_validator.probes import ACCOUNT_PROBES, request_path
from tests.support import FakeGitHubClient, user_response

_TOKEN = "ghp_supersecretvalue"


def _factory(
    responses: dict[str, GitHubResponse | Exception],
    seen: list[tuple[str, int]],
):
    def factory(token: str, timeout: int) -> FakeGitHubClient:
        seen.append((token, timeout))
        return FakeGitHubClient(responses, default=GitHubResponse(200, {}, None))

    return factory


def _refuse(token: str, timeout: int) -> FakeGitHubClient:
    raise AssertionError((token, timeout))


def _granted_user() -> dict[str, GitHubResponse | Exception]:
    responses: dict[str, GitHubResponse | Exception] = {
        request_path(probe.endpoint): GitHubResponse(200, {}, None)
        for probe in ACCOUNT_PROBES
    }
    responses["/user"] = user_response()
    return responses


def test_help_and_version_exit_zero(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert PROGRAM_VERSION_STRING in capsys.readouterr().out


def test_missing_token_exits_two(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    with pytest.raises(SystemExit) as exc:
        main([])
    captured = capsys.readouterr()
    assert exc.value.code == 2
    assert "A token is required. Pass --token or set GITHUB_TOKEN." in captured.err


def test_token_flag_overrides_environment(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_fromenv")
    seen: list[tuple[str, int]] = []
    with pytest.raises(SystemExit) as exc:
        main(
            ["--token", _TOKEN, "--timeout", "3"],
            client_factory=_factory(_granted_user(), seen),
        )
    captured = capsys.readouterr()
    assert exc.value.code == 0
    assert seen == [(_TOKEN, 3)]
    assert _TOKEN not in captured.out + captured.err
    assert "ghp_fromenv" not in captured.out + captured.err
    assert "Account permissions" in captured.out
    assert "Target permissions" not in captured.out
    assert "not checked" not in captured.out


def test_blank_token_does_not_use_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_fromenv")
    seen: list[tuple[str, int]] = []
    with pytest.raises(SystemExit) as exc:
        main(["--token", "  "], client_factory=_factory({}, seen))
    assert exc.value.code == 2
    assert seen == []


@pytest.mark.parametrize("value", ["0", "-1", "abc", "1.5"])
def test_bad_timeout_exits_two(value: str) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--timeout", value, "--token", _TOKEN], client_factory=_refuse)
    assert exc.value.code == 2


@pytest.mark.parametrize(
    "value",
    ["nope", "octo/", "/hello", "octo/hello/extra", "octo/hel lo"],
)
def test_bad_repo_exits_two(value: str) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--token", _TOKEN, "--repo", value], client_factory=_refuse)
    assert exc.value.code == 2


def test_blank_org_exits_two() -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--token", _TOKEN, "--org", " "], client_factory=_refuse)
    assert exc.value.code == 2


@pytest.mark.parametrize("value", ["ac me", "acme/team"])
def test_org_must_be_a_single_name(
    value: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--token", "github_pat_fine", "--org", value], client_factory=_refuse)
    captured = capsys.readouterr()
    assert exc.value.code == 2
    assert "--org must be a single name." in captured.err
    assert value not in captured.err


def test_token_whitespace_is_removed(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "  ghp_fromenv\n")
    seen: list[tuple[str, int]] = []
    with pytest.raises(SystemExit) as exc:
        main([], client_factory=_factory(_granted_user(), seen))
    assert exc.value.code == 0
    assert seen == [("ghp_fromenv", 10)]
    assert "ghp_fromenv" not in capsys.readouterr().out


def test_client_is_closed_after_the_run() -> None:
    seen: list[FakeGitHubClient] = []

    def factory(token: str, timeout: int) -> FakeGitHubClient:
        client = FakeGitHubClient(
            _granted_user(),
            default=GitHubResponse(200, {}, None),
        )
        seen.append(client)
        return client

    with pytest.raises(SystemExit) as exc:
        main(["--token", _TOKEN], client_factory=factory)
    assert exc.value.code == 0
    assert seen[0].closed is True


def test_unknown_flag_does_not_print_its_value(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--tokn", _TOKEN])
    captured = capsys.readouterr()
    assert exc.value.code == 2
    assert "unrecognized arguments." in captured.err
    assert _TOKEN not in captured.err


def test_refresh_token_skips_the_client(capsys: pytest.CaptureFixture[str]) -> None:
    def factory(token: str, timeout: int) -> FakeGitHubClient:
        raise AssertionError(token)

    with pytest.raises(SystemExit) as exc:
        main(["--token", "ghr_refreshvalue"], client_factory=factory)
    captured = capsys.readouterr()
    assert exc.value.code == 2
    assert "Refresh token" in captured.out
    assert "Account permissions" not in captured.out
    assert "ghr_refreshvalue" not in captured.out + captured.err


def test_user_401_prints_no_tables(capsys: pytest.CaptureFixture[str]) -> None:
    responses: dict[str, GitHubResponse | Exception] = {
        "/user": GitHubUnauthorizedError("GitHub rejected the token (HTTP 401).")
    }
    seen: list[tuple[str, int]] = []
    with pytest.raises(SystemExit) as exc:
        main(["--token", _TOKEN], client_factory=_factory(responses, seen))
    captured = capsys.readouterr()
    assert exc.value.code == 1
    assert "Summary" not in captured.out
    assert "GitHub rejected the token (HTTP 401)." in captured.out
    assert _TOKEN not in captured.out + captured.err


def test_later_401_prints_tables_gathered_so_far(
    capsys: pytest.CaptureFixture[str],
) -> None:
    responses = _granted_user()
    responses["/user/emails"] = GitHubUnauthorizedError(
        "GitHub rejected the token (HTTP 401)."
    )
    seen: list[tuple[str, int]] = []
    with pytest.raises(SystemExit) as exc:
        main(
            ["--token", _TOKEN, "--org", "acme", "--repo", "octo/hello"],
            client_factory=_factory(responses, seen),
        )
    captured = capsys.readouterr()
    assert exc.value.code == 1
    assert "Profile" in captured.out
    assert "GitHub rejected the token (HTTP 401)." in captured.out
    assert "/orgs/acme" not in captured.out


@pytest.mark.parametrize(
    ("token", "label"),
    [
        ("github_pat_fine", "Fine-grained personal access token"),
        ("ghs_install", "GitHub App installation or Actions token"),
        ("not-a-token", "Unknown"),
    ],
)
def test_resource_token_requires_a_target(
    token: str,
    label: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def factory(token_value: str, timeout: int) -> FakeGitHubClient:
        raise AssertionError(token_value)

    with pytest.raises(SystemExit) as exc:
        main(["--token", token], client_factory=factory)
    captured = capsys.readouterr()
    assert exc.value.code == 2
    assert captured.err == f"{label} requires --org or --repo.\n"
    assert token not in captured.err
    assert captured.out == ""


@pytest.mark.parametrize("token", ["ghp_classic", "gho_oauth", "ghu_user"])
def test_scope_header_tokens_do_not_need_a_target(
    token: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    seen: list[tuple[str, int]] = []
    with pytest.raises(SystemExit) as exc:
        main(["--token", token], client_factory=_factory(_granted_user(), seen))
    captured = capsys.readouterr()
    assert exc.value.code == 0
    assert seen == [(token, 10)]
    assert "Account permissions" in captured.out
    assert "Target permissions" not in captured.out
    assert "not checked" not in captured.out


def test_one_target_omits_the_other_catalog(capsys: pytest.CaptureFixture[str]) -> None:
    seen: list[tuple[str, int]] = []
    with pytest.raises(SystemExit) as exc:
        main(
            ["--token", "github_pat_fine", "--repo", "octo/hello"],
            client_factory=_factory(_granted_user(), seen),
        )
    captured = capsys.readouterr()
    assert exc.value.code == 0
    assert seen == [("github_pat_fine", 10)]
    assert "Target permissions" in captured.out
    assert "/repos/octo/hello" in captured.out
    assert "GET /orgs/" not in captured.out
    assert "not checked" not in captured.out


def test_keyboard_interrupt_exits_130(capsys: pytest.CaptureFixture[str]) -> None:
    def factory(token: str, timeout: int) -> FakeGitHubClient:
        raise KeyboardInterrupt

    with pytest.raises(SystemExit) as exc:
        main(["--token", _TOKEN], client_factory=factory)
    assert exc.value.code == 130
    assert "Interrupted." in capsys.readouterr().err
