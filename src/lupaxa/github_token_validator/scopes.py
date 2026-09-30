"""Local descriptions for scopes GitHub returns."""

from __future__ import annotations

SCOPE_ALLOWS: dict[str, str] = {
    "repo": (
        "Full read and write access to public and private repository code, "
        "statuses, invitations, collaborators, deployments, and webhooks, "
        "plus related organisation resources that this scope includes"
    ),
    "repo:status": ("Read and write commit statuses without repository code access"),
    "repo_deployment": (
        "Read and write deployment statuses without repository code access"
    ),
    "public_repo": (
        "Read and write access limited to public repositories, "
        "including starring public repositories"
    ),
    "repo:invite": (
        "Accept or decline repository collaboration invitations without code access"
    ),
    "security_events": (
        "Read and write code-scanning security events without repository code access"
    ),
    "admin:repo_hook": "Read, write, ping, and delete repository hooks",
    "write:repo_hook": "Read, write, and ping repository hooks",
    "read:repo_hook": "Read and ping repository hooks",
    "admin:org": (
        "Full control of the organisation, its teams, projects, and memberships"
    ),
    "write:org": "Read and write organisation membership and organisation projects",
    "read:org": (
        "Read organisation membership, organisation projects, and team membership"
    ),
    "admin:public_key": "Full control of public keys",
    "write:public_key": "Create, list, and view public keys",
    "read:public_key": "List and view public keys",
    "admin:org_hook": (
        "Read, write, ping, and delete organisation hooks created by this token"
    ),
    "gist": "Write gists",
    "notifications": (
        "Read notifications, mark threads read, watch or unwatch repositories, "
        "and manage thread subscriptions"
    ),
    "user": "Read and write profile info. Includes `user:email` and `user:follow`",
    "read:user": "Read profile data",
    "user:email": "Read email addresses",
    "user:follow": "Follow and unfollow users",
    "project": "Read and write user and organisation projects",
    "read:project": "Read user and organisation projects",
    "delete_repo": "Delete repositories the token can administer",
    "write:packages": "Upload and publish GitHub Packages",
    "read:packages": "Download and install GitHub Packages",
    "delete:packages": "Delete GitHub Packages",
    "admin:gpg_key": "Full control of GPG keys",
    "write:gpg_key": "Create, list, and view GPG keys",
    "read:gpg_key": "List and view GPG keys",
    "admin:ssh_signing_key": "Full control of SSH signing keys",
    "write:ssh_signing_key": "Create, list, and view SSH signing keys",
    "read:ssh_signing_key": "List and view SSH signing keys",
    "codespace": "Create and manage codespaces",
    "workflow": "Add and update GitHub Actions workflow files",
    "read:audit_log": "Read audit log data",
    "offline_access": "Request an expiring access token and a refresh token",
}


def scope_names(header: str | None) -> tuple[str, ...]:
    """Split ``X-OAuth-Scopes`` in header order."""
    if header is None:
        return ("none",)
    names = tuple(part.strip() for part in header.split(",") if part.strip())
    if not names:
        return ("none",)
    return names


def allows_text(scope: str) -> str:
    """Return the local sentence for ``scope``."""
    if scope == "none":
        return "GitHub sent no scopes."
    return SCOPE_ALLOWS.get(scope, "No local description.")


def accepted_permission_rows(header: str | None) -> tuple[tuple[str, str], ...]:
    """Split ``X-Accepted-GitHub-Permissions`` into permission and access."""
    if header is None:
        return (("none", "GitHub sent no accepted permissions."),)
    rows: list[tuple[str, str]] = []
    for part in header.replace(",", ";").split(";"):
        name, separator, access = part.strip().partition("=")
        if separator != "=" or name == "" or access.strip() == "":
            continue
        rows.append((name, access.strip()))
    if not rows:
        return (("none", "GitHub sent no accepted permissions."),)
    return tuple(rows)
