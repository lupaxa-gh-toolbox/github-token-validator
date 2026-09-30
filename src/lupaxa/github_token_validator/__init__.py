"""Report what a GitHub token is allowed to do."""

from __future__ import annotations

from collections.abc import Callable

__all__ = ["main"]


def __getattr__(name: str) -> Callable[..., None]:
    """Load ``main`` on first use so other imports stay light."""
    if name == "main":
        from lupaxa.github_token_validator.cli import main

        return main
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
