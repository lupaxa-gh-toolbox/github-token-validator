"""The runner records probe results and stops on auth or transport failure."""

from __future__ import annotations

from lupaxa.github_token_validator.classify import classify_token
from lupaxa.github_token_validator.client import GitHubResponse, GitHubUnauthorizedError
from lupaxa.github_token_validator.probes import (
    ACCOUNT_PROBES,
    request_path,
    run_validation,
)
from tests.support import FakeGitHubClient, user_response


def _granted() -> GitHubResponse:
    return GitHubResponse(200, {}, None)


def test_refresh_token_makes_no_request() -> None:
    client = FakeGitHubClient({})
    report = run_validation(
        kind=classify_token("ghr_refresh"),
        org="acme",
        repo=("octo", "hello"),
        client=client,
    )
    assert client.calls == []
    assert report.exit_code == 2
    assert report.kind_label == "Refresh token"
    assert report.login == "not requested"
    assert report.scopes_raw == "none"
    assert report.rate_limit == "not requested"
    assert report.show_summary is True
    assert report.show_scopes is False
    assert report.show_account is False
    assert report.show_target is False


def test_user_failure_hides_tables() -> None:
    client = FakeGitHubClient(
        {"/user": GitHubUnauthorizedError("GitHub rejected the token (HTTP 401).")}
    )
    report = run_validation(
        kind=classify_token("ghp_token"),
        org=None,
        repo=None,
        client=client,
    )
    assert report.exit_code == 1
    assert report.error == "GitHub rejected the token (HTTP 401)."
    assert report.show_summary is False
    assert client.calls == [("/user", True)]


def test_profile_reuses_the_user_response_and_scopes_stay_in_order() -> None:
    responses: dict[str, GitHubResponse | Exception] = {
        request_path(probe.endpoint): _granted() for probe in ACCOUNT_PROBES
    }
    responses["/user"] = user_response(scopes="read:user, gist")
    client = FakeGitHubClient(responses)
    report = run_validation(
        kind=classify_token("github_pat_fine"),
        org=None,
        repo=None,
        client=client,
    )
    assert client.calls[0] == ("/user", True)
    assert [path for path, _read in client.calls].count("/user") == 1
    assert report.login == "octocat"
    assert report.scopes_raw == "read:user, gist"
    assert [scope for scope, _allows in report.scope_rows] == ["read:user", "gist"]
    assert report.account_rows[0].check == "Profile"
    assert report.account_rows[0].result == "granted"
    assert report.rate_reset == "2023-11-14 22:13:20"
    assert report.exit_code == 0
    assert report.target_rows == ()
    assert report.show_target is False
    assert not any(
        path.startswith("/orgs/") or path.startswith("/repos/")
        for path, _read in client.calls
    )


def test_missing_login_and_scopes() -> None:
    responses: dict[str, GitHubResponse | Exception] = {
        request_path(probe.endpoint): _granted() for probe in ACCOUNT_PROBES
    }
    responses["/user"] = user_response(login=None, scopes=None)
    client = FakeGitHubClient(responses, default=_granted())
    report = run_validation(
        kind=classify_token("ghs_install"),
        org="acme",
        repo=None,
        client=client,
    )
    assert report.login == "unknown"
    assert report.scopes_raw == "none"
    assert report.scope_rows == (("none", "GitHub sent no accepted permissions."),)
    assert report.account_rows == ()
    assert report.show_account is False
    assert "/orgs/acme" in [path for path, _read in client.calls]
    assert "/user/emails" not in [path for path, _read in client.calls]


def test_installation_token_lists_accepted_permissions() -> None:
    user = user_response(login=None, scopes=None)
    headers = {
        **user.headers,
        "X-Accepted-GitHub-Permissions": "contents=read; metadata=read",
    }
    client = FakeGitHubClient(
        {"/user": GitHubResponse(403, headers, None)},
        default=_granted(),
    )
    report = run_validation(
        kind=classify_token("ghs_install"),
        org=None,
        repo=("octo", "hello"),
        client=client,
    )
    assert report.scopes_raw == "contents=read; metadata=read"
    assert report.scope_rows == (("contents", "read"), ("metadata", "read"))
    assert report.show_account is False
    assert "/repos/octo/hello" in [path for path, _read in client.calls]


def test_fine_grained_token_without_scopes_says_so() -> None:
    responses: dict[str, GitHubResponse | Exception] = {
        request_path(probe.endpoint): _granted() for probe in ACCOUNT_PROBES
    }
    responses["/user"] = user_response(scopes=None)
    report = run_validation(
        kind=classify_token("github_pat_fine"),
        org="acme",
        repo=None,
        client=FakeGitHubClient(responses, default=_granted()),
    )
    assert report.scopes_raw == "none"
    assert report.scope_rows == (
        ("none", "Fine-grained tokens do not return OAuth scopes."),
    )
    assert report.show_account is True


def test_whitespace_only_scope_header_is_none() -> None:
    responses: dict[str, GitHubResponse | Exception] = {
        request_path(probe.endpoint): _granted() for probe in ACCOUNT_PROBES
    }
    responses["/user"] = user_response(scopes="   ")
    report = run_validation(
        kind=classify_token("ghp_token"),
        org=None,
        repo=None,
        client=FakeGitHubClient(responses),
    )
    assert report.scopes_raw == "none"
    assert report.scope_rows == (("none", "GitHub sent no scopes."),)


def test_later_401_keeps_completed_rows_and_stops() -> None:
    responses: dict[str, GitHubResponse | Exception] = {
        request_path(probe.endpoint): _granted() for probe in ACCOUNT_PROBES
    }
    responses["/user"] = user_response()
    responses["/user/emails"] = GitHubUnauthorizedError(
        "GitHub rejected the token (HTTP 401)."
    )
    client = FakeGitHubClient(responses)
    report = run_validation(
        kind=classify_token("ghp_token"),
        org="acme",
        repo=("octo", "hello"),
        client=client,
    )
    assert report.exit_code == 1
    assert [row.check for row in report.account_rows] == ["Profile"]
    assert report.target_rows == ()
    assert report.show_account is True
    assert report.show_target is False
    paths = [path for path, _read in client.calls]
    assert "/user/following" not in paths
    assert "/orgs/acme" not in paths


def test_other_status_continues() -> None:
    responses: dict[str, GitHubResponse | Exception] = {
        request_path(probe.endpoint): _granted() for probe in ACCOUNT_PROBES
    }
    responses["/user"] = user_response()
    responses["/user/emails"] = GitHubResponse(500, {}, None)
    responses["/user/following?per_page=1"] = GitHubResponse(403, {}, None)
    responses["/gists?per_page=1"] = GitHubResponse(404, {}, None)
    report = run_validation(
        kind=classify_token("ghp_token"),
        org=None,
        repo=None,
        client=FakeGitHubClient(responses),
    )
    by_check = {row.check: row.result for row in report.account_rows}
    assert by_check["Emails"] == "error 500"
    assert by_check["Following"] == "denied"
    assert by_check["Gists"] == "not applicable"
    assert report.exit_code == 0


def test_both_targets_are_requested_when_flags_are_set() -> None:
    responses: dict[str, GitHubResponse | Exception] = {
        request_path(probe.endpoint): _granted() for probe in ACCOUNT_PROBES
    }
    responses["/user"] = user_response()
    client = FakeGitHubClient(responses, default=_granted())
    report = run_validation(
        kind=classify_token("ghp_token"),
        org="acme",
        repo=("octo", "hello"),
        client=client,
    )
    paths = [path for path, _read in client.calls]
    assert "/orgs/acme" in paths
    assert "/orgs/acme/members?per_page=1" in paths
    assert "/repos/octo/hello/contents" in paths
    assert "/repos/octo/hello/commits?per_page=1" in paths
    org_rows = [row for row in report.target_rows if row.target == "organisation"]
    repo_rows = [row for row in report.target_rows if row.target == "repository"]
    assert org_rows[0].endpoint == "GET /orgs/acme"
    assert repo_rows[1].endpoint == "GET /repos/octo/hello/contents"
    assert all(row.result == "granted" for row in report.target_rows)
