"""Catalog rows and status labels do not perform I/O."""

from __future__ import annotations

from lupaxa.github_token_validator.probes import (
    ACCOUNT_PROBES,
    ORGANISATION_PROBES,
    REPOSITORY_PROBES,
    bind_endpoint,
    header_value,
    rate_limit_fields,
    request_path,
    status_result,
)


def test_catalog_checks_match_the_spec() -> None:
    assert [probe.check for probe in ACCOUNT_PROBES] == [
        "Profile",
        "Emails",
        "Following",
        "Organisations",
        "Org membership roles",
        "Gists",
        "Notifications",
        "Public keys",
        "GPG keys",
        "SSH signing keys",
        "Packages",
        "Repository list",
        "Codespaces",
        "Installations",
    ]
    assert [probe.check for probe in ORGANISATION_PROBES] == [
        "Organisation",
        "Members",
        "Hooks",
        "Audit log",
        "Actions permissions",
        "Packages",
    ]
    assert [probe.check for probe in REPOSITORY_PROBES] == [
        "Repository",
        "Contents",
        "Hooks",
        "Workflows",
        "Deployments",
        "Invitations",
        "Code scanning",
        "Commits",
    ]
    assert ACCOUNT_PROBES[0].endpoint == "GET /user"
    assert ORGANISATION_PROBES[0].endpoint == "GET /orgs/{org}"
    assert REPOSITORY_PROBES[1].endpoint == "GET /repos/{owner}/{repo}/contents"
    assert all(
        probe.meaning.strip()
        for probe in (*ACCOUNT_PROBES, *ORGANISATION_PROBES, *REPOSITORY_PROBES)
    )


def test_status_result_labels() -> None:
    assert status_result(200) == "granted"
    assert status_result(204) == "granted"
    assert status_result(403) == "denied"
    assert status_result(404) == "not applicable"
    assert status_result(500) == "error 500"


def test_request_path_and_binding() -> None:
    assert (
        request_path("GET /user/following?per_page=1") == "/user/following?per_page=1"
    )
    bound = bind_endpoint(
        "GET /repos/{owner}/{repo}/contents",
        owner="octo",
        repo="hello",
    )
    assert bound == "GET /repos/octo/hello/contents"
    encoded = bind_endpoint("GET /orgs/{org}", org="acme#")
    assert encoded == "GET /orgs/acme%23"


def test_rate_limit_fields() -> None:
    assert rate_limit_fields(
        {
            "x-ratelimit-limit": "5000",
            "X-RateLimit-Used": "7",
            "X-RateLimit-Remaining": "4993",
            "X-RateLimit-Reset": "1700000000",
        }
    ) == ("5000", "7", "4993", "2023-11-14 22:13:20")
    assert rate_limit_fields({}) == ("unknown", "unknown", "unknown", "unknown")
    assert header_value({"X-OAuth-Scopes": "  "}, "x-oauth-scopes") is None
