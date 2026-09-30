"""Read-only probe catalog."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from urllib.parse import quote

from lupaxa.github_token_validator.classify import TokenKind
from lupaxa.github_token_validator.client import (
    GitHubClient,
    GitHubRateLimitError,
    GitHubResponse,
    GitHubTransportError,
    GitHubUnauthorizedError,
)
from lupaxa.github_token_validator.constants import (
    EXIT_FAILURE,
    EXIT_SUCCESS,
    EXIT_USAGE,
)
from lupaxa.github_token_validator.scopes import (
    accepted_permission_rows,
    allows_text,
    scope_names,
)


@dataclass(frozen=True, slots=True)
class Probe:
    """One catalog row."""

    check: str
    endpoint: str
    meaning: str


def status_result(status_code: int) -> str:
    """Map an HTTP status to a row result."""
    if status_code in (200, 204):
        return "granted"
    if status_code == 403:
        return "denied"
    if status_code == 404:
        return "not applicable"
    return f"error {status_code}"


def request_path(endpoint: str) -> str:
    """Return the path and query from a ``GET`` endpoint label."""
    method, _, path = endpoint.partition(" ")
    if method != "GET" or not path.startswith("/"):
        raise ValueError(endpoint)
    return path


def bind_endpoint(
    endpoint: str,
    *,
    org: str | None = None,
    owner: str | None = None,
    repo: str | None = None,
) -> str:
    """Fill placeholders whose arguments were passed."""
    text = endpoint
    if org is not None:
        text = text.replace("{org}", quote(org, safe=""))
    if owner is not None:
        text = text.replace("{owner}", quote(owner, safe=""))
    if repo is not None:
        text = text.replace("{repo}", quote(repo, safe=""))
    return text


def header_value(headers: Mapping[str, str], name: str) -> str | None:
    """Return a header value, ignoring case and blank text."""
    wanted = name.lower()
    for key, value in headers.items():
        if key.lower() == wanted and value.strip() != "":
            return value
    return None


def rate_limit_fields(headers: Mapping[str, str]) -> tuple[str, str, str, str]:
    """Return limit, used, remaining, and UTC reset."""
    limit = header_value(headers, "X-RateLimit-Limit") or "unknown"
    used = header_value(headers, "X-RateLimit-Used") or "unknown"
    remaining = header_value(headers, "X-RateLimit-Remaining") or "unknown"
    raw_reset = header_value(headers, "X-RateLimit-Reset")
    if raw_reset is None or not raw_reset.isdigit():
        return (limit, used, remaining, "unknown")
    reset = datetime.fromtimestamp(int(raw_reset), tz=UTC).strftime("%Y-%m-%d %H:%M:%S")
    return (limit, used, remaining, reset)


ACCOUNT_PROBES: tuple[Probe, ...] = (
    Probe("Profile", "GET /user", "Read the authenticated user profile"),
    Probe(
        "Emails", "GET /user/emails", "Read the authenticated user's email addresses"
    ),
    Probe(
        "Following",
        "GET /user/following?per_page=1",
        "Read the users this account follows",
    ),
    Probe(
        "Organisations", "GET /user/orgs?per_page=1", "Read organisation memberships"
    ),
    Probe(
        "Org membership roles",
        "GET /user/memberships/orgs?per_page=1",
        "Read organisation membership roles",
    ),
    Probe("Gists", "GET /gists?per_page=1", "Read gists"),
    Probe("Notifications", "GET /notifications?per_page=1", "Read notifications"),
    Probe("Public keys", "GET /user/keys?per_page=1", "Read public keys"),
    Probe("GPG keys", "GET /user/gpg_keys?per_page=1", "Read GPG keys"),
    Probe(
        "SSH signing keys",
        "GET /user/ssh_signing_keys?per_page=1",
        "Read SSH signing keys",
    ),
    Probe(
        "Packages",
        "GET /user/packages?package_type=npm&per_page=1",
        "Read GitHub Packages",
    ),
    Probe(
        "Repository list",
        "GET /user/repos?per_page=1",
        "Read whether the repository list is allowed. Do not print repository names",
    ),
    Probe("Codespaces", "GET /user/codespaces?per_page=1", "Read codespaces"),
    Probe(
        "Installations",
        "GET /user/installations?per_page=1",
        "Read GitHub App installations",
    ),
)

ORGANISATION_PROBES: tuple[Probe, ...] = (
    Probe("Organisation", "GET /orgs/{org}", "Read the organisation profile"),
    Probe(
        "Members",
        "GET /orgs/{org}/members?per_page=1",
        "Read organisation members. Do not print logins",
    ),
    Probe("Hooks", "GET /orgs/{org}/hooks?per_page=1", "Read organisation hooks"),
    Probe(
        "Audit log",
        "GET /orgs/{org}/audit-log?per_page=1",
        "Read the organisation audit log",
    ),
    Probe(
        "Actions permissions",
        "GET /orgs/{org}/actions/permissions",
        "Read organisation Actions permissions",
    ),
    Probe(
        "Packages",
        "GET /orgs/{org}/packages?package_type=npm&per_page=1",
        "Read organisation packages",
    ),
)

REPOSITORY_PROBES: tuple[Probe, ...] = (
    Probe("Repository", "GET /repos/{owner}/{repo}", "Read repository metadata"),
    Probe(
        "Contents",
        "GET /repos/{owner}/{repo}/contents",
        "Read repository contents. Do not print paths",
    ),
    Probe(
        "Hooks", "GET /repos/{owner}/{repo}/hooks?per_page=1", "Read repository hooks"
    ),
    Probe(
        "Workflows",
        "GET /repos/{owner}/{repo}/actions/workflows?per_page=1",
        "Read Actions workflows. Do not print workflow names",
    ),
    Probe(
        "Deployments",
        "GET /repos/{owner}/{repo}/deployments?per_page=1",
        "Read deployments",
    ),
    Probe(
        "Invitations",
        "GET /repos/{owner}/{repo}/invitations?per_page=1",
        "Read repository invitations",
    ),
    Probe(
        "Code scanning",
        "GET /repos/{owner}/{repo}/code-scanning/alerts?per_page=1",
        "Read code-scanning alerts",
    ),
    Probe(
        "Commits",
        "GET /repos/{owner}/{repo}/commits?per_page=1",
        "Read commits. Do not print commit messages",
    ),
)


@dataclass(frozen=True, slots=True)
class ProbeRow:
    """One rendered permission check."""

    target: str
    check: str
    endpoint: str
    result: str
    meaning: str


@dataclass(frozen=True, slots=True)
class RunReport:
    """Tables and the process exit code."""

    kind_label: str
    login: str
    scopes_raw: str
    scope_rows: tuple[tuple[str, str], ...]
    rate_limit: str
    rate_used: str
    rate_remaining: str
    rate_reset: str
    account_rows: tuple[ProbeRow, ...]
    target_rows: tuple[ProbeRow, ...]
    error: str | None
    exit_code: int
    show_summary: bool
    show_scopes: bool
    show_account: bool
    show_target: bool


@dataclass(frozen=True, slots=True)
class _ProbeStep:
    """A completed row or a row awaiting one GET."""

    row: ProbeRow
    path: str | None


def run_validation(
    *,
    kind: TokenKind,
    org: str | None,
    repo: tuple[str, str] | None,
    client: GitHubClient | None,
) -> RunReport:
    """Probe the token, or return the refresh-token summary."""
    if not kind.calls_api:
        return _not_requested(kind.label)
    if client is None:
        raise ValueError("client is required")
    try:
        user = client.get("/user", read_login=True)
    except (GitHubUnauthorizedError, GitHubRateLimitError, GitHubTransportError) as exc:
        return _hidden_failure(kind.label, str(exc))
    report = _report_from_user(kind, user)
    if kind.checks_account:
        account_rows, error = _collect(client, _account_steps(user))
        if error is not None:
            return _aborted(report, account_rows, (), error)
    else:
        account_rows = ()
    target_rows, error = _collect(client, _target_steps(org, repo))
    if error is not None:
        return _aborted(report, account_rows, target_rows, error)
    return replace(
        report,
        account_rows=account_rows,
        target_rows=target_rows,
        exit_code=EXIT_SUCCESS,
        show_account=bool(account_rows),
        show_target=bool(target_rows),
    )


def _not_requested(kind_label: str) -> RunReport:
    """Return the summary for a token that cannot call the API."""
    return RunReport(
        kind_label=kind_label,
        login="not requested",
        scopes_raw="none",
        scope_rows=(),
        rate_limit="not requested",
        rate_used="not requested",
        rate_remaining="not requested",
        rate_reset="not requested",
        account_rows=(),
        target_rows=(),
        error=None,
        exit_code=EXIT_USAGE,
        show_summary=True,
        show_scopes=False,
        show_account=False,
        show_target=False,
    )


def _report_from_user(kind: TokenKind, user: GitHubResponse) -> RunReport:
    """Build the initial visible report from GET /user."""
    scopes_raw, scope_rows = _permission_fields(kind, user.headers)
    limit, used, remaining, reset = rate_limit_fields(user.headers)
    return RunReport(
        kind_label=kind.label,
        login=user.login or "unknown",
        scopes_raw=scopes_raw,
        scope_rows=scope_rows,
        rate_limit=limit,
        rate_used=used,
        rate_remaining=remaining,
        rate_reset=reset,
        account_rows=(),
        target_rows=(),
        error=None,
        exit_code=EXIT_SUCCESS,
        show_summary=True,
        show_scopes=True,
        show_account=True,
        show_target=True,
    )


def _account_steps(user: GitHubResponse) -> tuple[_ProbeStep, ...]:
    """Return the completed Profile step followed by pending account steps."""
    profile = ACCOUNT_PROBES[0]
    completed = _ProbeStep(
        _row("", profile, profile.endpoint, status_result(user.status_code)),
        None,
    )
    pending = tuple(
        _ProbeStep(_row("", probe, probe.endpoint, ""), request_path(probe.endpoint))
        for probe in ACCOUNT_PROBES[1:]
    )
    return (completed, *pending)


def _target_steps(
    org: str | None,
    repo: tuple[str, str] | None,
) -> tuple[_ProbeStep, ...]:
    """Return organisation steps followed by repository steps."""
    organisation = _bound_steps(
        target="organisation",
        probes=ORGANISATION_PROBES,
        enabled=org is not None,
        org=org,
    )
    owner, name = repo if repo is not None else (None, None)
    repository = _bound_steps(
        target="repository",
        probes=REPOSITORY_PROBES,
        enabled=repo is not None,
        owner=owner,
        repo=name,
    )
    return (*organisation, *repository)


def _bound_steps(
    *,
    target: str,
    probes: tuple[Probe, ...],
    enabled: bool,
    org: str | None = None,
    owner: str | None = None,
    repo: str | None = None,
) -> tuple[_ProbeStep, ...]:
    """Bind one target's endpoints when that target was requested."""
    if not enabled:
        return ()
    return tuple(
        _pending_bound_step(target, probe, org=org, owner=owner, repo=repo)
        for probe in probes
    )


def _pending_bound_step(
    target: str,
    probe: Probe,
    *,
    org: str | None,
    owner: str | None,
    repo: str | None,
) -> _ProbeStep:
    """Create a pending step with a bound endpoint."""
    endpoint = bind_endpoint(probe.endpoint, org=org, owner=owner, repo=repo)
    return _ProbeStep(_row(target, probe, endpoint, ""), request_path(endpoint))


def _row(target: str, probe: Probe, endpoint: str, result: str) -> ProbeRow:
    """Build one result row."""
    return ProbeRow(target, probe.check, endpoint, result, probe.meaning)


def _collect(
    client: GitHubClient,
    steps: tuple[_ProbeStep, ...],
) -> tuple[tuple[ProbeRow, ...], str | None]:
    """Complete steps until the first authentication or transport failure."""
    rows: list[ProbeRow] = []
    for step in steps:
        if step.path is None:
            rows.append(step.row)
            continue
        result = _request(client, step.path)
        if isinstance(result, str):
            return (tuple(rows), result)
        rows.append(replace(step.row, result=status_result(result.status_code)))
    return (tuple(rows), None)


def _request(client: GitHubClient, path: str) -> GitHubResponse | str:
    """Return one response, or the client failure text."""
    try:
        return client.get(path)
    except (GitHubUnauthorizedError, GitHubRateLimitError, GitHubTransportError) as exc:
        return str(exc)


def _permission_fields(
    kind: TokenKind,
    headers: Mapping[str, str],
) -> tuple[str, tuple[tuple[str, str], ...]]:
    """Choose the scope or accepted-permission rows for this token kind."""
    if kind.permission_source == "accepted":
        header = header_value(headers, "X-Accepted-GitHub-Permissions")
        return header or "none", accepted_permission_rows(header)
    scopes_header = header_value(headers, "X-OAuth-Scopes")
    if kind.permission_source == "fine_grained" and scopes_header is None:
        text = "Fine-grained tokens do not return OAuth scopes."
        return "none", (("none", text),)
    names = scope_names(scopes_header)
    return scopes_header or "none", tuple((name, allows_text(name)) for name in names)


def _hidden_failure(kind_label: str, error: str) -> RunReport:
    """Return an initial failure with every table hidden."""
    return RunReport(
        kind_label=kind_label,
        login="unknown",
        scopes_raw="none",
        scope_rows=(),
        rate_limit="unknown",
        rate_used="unknown",
        rate_remaining="unknown",
        rate_reset="unknown",
        account_rows=(),
        target_rows=(),
        error=error,
        exit_code=EXIT_FAILURE,
        show_summary=False,
        show_scopes=False,
        show_account=False,
        show_target=False,
    )


def _aborted(
    report: RunReport,
    account_rows: tuple[ProbeRow, ...],
    target_rows: tuple[ProbeRow, ...],
    error: str,
) -> RunReport:
    """Keep completed rows and hide empty result tables after a failure."""
    return replace(
        report,
        account_rows=account_rows,
        target_rows=target_rows,
        error=error,
        exit_code=EXIT_FAILURE,
        show_account=bool(account_rows),
        show_target=bool(target_rows),
    )
