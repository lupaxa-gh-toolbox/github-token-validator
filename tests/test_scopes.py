"""Scope text comes from the local dictionary and the header order."""

from __future__ import annotations

from lupaxa.github_token_validator.scopes import (
    SCOPE_ALLOWS,
    accepted_permission_rows,
    allows_text,
    scope_names,
)

_EXPECTED_SCOPES = frozenset(
    {
        "repo",
        "repo:status",
        "repo_deployment",
        "public_repo",
        "repo:invite",
        "security_events",
        "admin:repo_hook",
        "write:repo_hook",
        "read:repo_hook",
        "admin:org",
        "write:org",
        "read:org",
        "admin:public_key",
        "write:public_key",
        "read:public_key",
        "admin:org_hook",
        "gist",
        "notifications",
        "user",
        "read:user",
        "user:email",
        "user:follow",
        "project",
        "read:project",
        "delete_repo",
        "write:packages",
        "read:packages",
        "delete:packages",
        "admin:gpg_key",
        "write:gpg_key",
        "read:gpg_key",
        "admin:ssh_signing_key",
        "write:ssh_signing_key",
        "read:ssh_signing_key",
        "codespace",
        "workflow",
        "read:audit_log",
        "offline_access",
    }
)


def test_dictionary_covers_the_spec_and_descriptions_are_not_empty() -> None:
    assert set(SCOPE_ALLOWS) == _EXPECTED_SCOPES
    for text in SCOPE_ALLOWS.values():
        assert text.strip() != ""


def test_parent_scope_does_not_invent_children() -> None:
    assert scope_names("repo") == ("repo",)


def test_header_order_is_preserved() -> None:
    assert scope_names(" read:user, gist ") == ("read:user", "gist")


def test_missing_or_blank_header_is_none() -> None:
    assert scope_names(None) == ("none",)
    assert scope_names("") == ("none",)
    assert scope_names(" , ") == ("none",)
    assert allows_text("none") == "GitHub sent no scopes."


def test_accepted_permissions_keep_header_order() -> None:
    header = "contents=read, metadata=read; pull_requests=write"
    assert accepted_permission_rows(header) == (
        ("contents", "read"),
        ("metadata", "read"),
        ("pull_requests", "write"),
    )
    assert accepted_permission_rows(None) == (
        ("none", "GitHub sent no accepted permissions."),
    )
    assert accepted_permission_rows("not a permission") == (
        ("none", "GitHub sent no accepted permissions."),
    )


def test_unknown_scope_has_no_local_description() -> None:
    assert allows_text("not-a-real-scope") == "No local description."


def test_repo_and_user_text_matches_the_spec() -> None:
    assert SCOPE_ALLOWS["repo"] == (
        "Full read and write access to public and private repository code, "
        "statuses, invitations, collaborators, deployments, and webhooks, "
        "plus related organisation resources that this scope includes"
    )
    assert SCOPE_ALLOWS["user"] == (
        "Read and write profile info. Includes `user:email` and `user:follow`"
    )
