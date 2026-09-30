"""Classify a GitHub token from its prefix."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PermissionSource = Literal["oauth", "accepted", "fine_grained"]


@dataclass(frozen=True, slots=True)
class TokenKind:
    """Prefix classification decided before any API call."""

    label: str
    calls_api: bool
    requires_target: bool
    checks_account: bool
    permission_source: PermissionSource


_UNKNOWN = TokenKind("Unknown", True, True, True, "oauth")

_PREFIXES: tuple[tuple[str, TokenKind], ...] = (
    (
        "github_pat_",
        TokenKind(
            "Fine-grained personal access token", True, True, True, "fine_grained"
        ),
    ),
    ("ghp_", TokenKind("Classic personal access token", True, False, True, "oauth")),
    ("gho_", TokenKind("OAuth access token", True, False, True, "oauth")),
    (
        "ghu_",
        TokenKind("GitHub App user-to-server token", True, False, True, "oauth"),
    ),
    (
        "ghs_",
        TokenKind(
            "GitHub App installation or Actions token", True, True, False, "accepted"
        ),
    ),
    ("ghr_", TokenKind("Refresh token", False, False, False, "oauth")),
)


def classify_token(token: str) -> TokenKind:
    """Return the kind for ``token`` from the first matching prefix."""
    for prefix, kind in _PREFIXES:
        if token.startswith(prefix):
            return kind
    return _UNKNOWN
