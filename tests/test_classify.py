"""Prefix classification does not call GitHub."""

from __future__ import annotations

import pytest

from lupaxa.github_token_validator.classify import classify_token


@pytest.mark.parametrize(
    ("token", "label", "calls_api", "requires_target", "checks_account", "source"),
    [
        ("ghp_classic", "Classic personal access token", True, False, True, "oauth"),
        (
            "github_pat_fine",
            "Fine-grained personal access token",
            True,
            True,
            True,
            "fine_grained",
        ),
        ("gho_oauth", "OAuth access token", True, False, True, "oauth"),
        ("ghu_user", "GitHub App user-to-server token", True, False, True, "oauth"),
        (
            "ghs_install",
            "GitHub App installation or Actions token",
            True,
            True,
            False,
            "accepted",
        ),
        ("ghr_refresh", "Refresh token", False, False, False, "oauth"),
        ("not-a-token", "Unknown", True, True, True, "oauth"),
        ("", "Unknown", True, True, True, "oauth"),
    ],
)
def test_classify_token(
    token: str,
    label: str,
    calls_api: bool,
    requires_target: bool,
    checks_account: bool,
    source: str,
) -> None:
    kind = classify_token(token)
    assert kind.label == label
    assert kind.calls_api is calls_api
    assert kind.requires_target is requires_target
    assert kind.checks_account is checks_account
    assert kind.permission_source == source
