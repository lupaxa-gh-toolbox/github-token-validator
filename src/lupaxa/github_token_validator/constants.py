"""Stable names, version, API constants, and exit codes."""

from __future__ import annotations

from typing import Final

__all__ = [
    "API_BASE_URL",
    "API_VERSION",
    "DEFAULT_TIMEOUT",
    "EXIT_FAILURE",
    "EXIT_INTERRUPTED",
    "EXIT_SUCCESS",
    "EXIT_USAGE",
    "PROGRAM_ALIAS",
    "PROGRAM_NAME",
    "PROGRAM_VERSION",
    "PROGRAM_VERSION_STRING",
    "PROJECT_NAME",
    "USER_AGENT",
]

PROGRAM_NAME: Final[str] = "github-token-validator"
PROGRAM_ALIAS: Final[str] = "gtv"
PROJECT_NAME: Final[str] = "lupaxa-github-token-validator"
PROGRAM_VERSION: Final[str] = "0.1.0"
PROGRAM_VERSION_STRING: Final[str] = f"{PROGRAM_NAME} v{PROGRAM_VERSION}"

API_BASE_URL: Final[str] = "https://api.github.com"
API_VERSION: Final[str] = "2022-11-28"
USER_AGENT: Final[str] = "lupaxa-github-token-validator"
DEFAULT_TIMEOUT: Final[int] = 10

EXIT_SUCCESS: Final[int] = 0
EXIT_FAILURE: Final[int] = 1
EXIT_USAGE: Final[int] = 2
EXIT_INTERRUPTED: Final[int] = 130
