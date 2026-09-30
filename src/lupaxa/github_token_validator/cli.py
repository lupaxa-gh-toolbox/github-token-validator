"""Command-line entry point."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
import os
import sys
from typing import NoReturn

from lupaxa.github_token_validator.classify import classify_token
from lupaxa.github_token_validator.client import GitHubClient, RequestsGitHubClient
from lupaxa.github_token_validator.constants import (
    DEFAULT_TIMEOUT,
    EXIT_INTERRUPTED,
    EXIT_USAGE,
    PROGRAM_NAME,
    PROGRAM_VERSION_STRING,
)
from lupaxa.github_token_validator.probes import run_validation
from lupaxa.github_token_validator.report import render_report


def default_client_factory(token: str, timeout: int) -> GitHubClient:
    """Build the requests client."""
    return RequestsGitHubClient(token, timeout)


def main(
    argv: Sequence[str] | None = None,
    *,
    client_factory: Callable[[str, int], GitHubClient] = default_client_factory,
) -> None:
    """Parse arguments, run probes, and exit."""
    try:
        code = execute(argv, client_factory, os.environ)
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        code = EXIT_INTERRUPTED
    raise SystemExit(code)


def execute(
    argv: Sequence[str] | None,
    client_factory: Callable[[str, int], GitHubClient],
    environ: Mapping[str, str],
) -> int:
    """Return the process exit code."""
    args = _parser().parse_args(None if argv is None else list(argv))
    token = _token(args.token, environ)
    if token is None:
        print(
            "A token is required. Pass --token or set GITHUB_TOKEN.",
            file=sys.stderr,
        )
        return EXIT_USAGE
    org = None if args.org is None else args.org.strip()
    if args.org is not None and org == "":
        print("--org must not be blank.", file=sys.stderr)
        return EXIT_USAGE
    if org is not None and not _single_name(org):
        print("--org must be a single name.", file=sys.stderr)
        return EXIT_USAGE
    kind = classify_token(token)
    if kind.requires_target and org is None and args.repo is None:
        print(f"{kind.label} requires --org or --repo.", file=sys.stderr)
        return EXIT_USAGE
    client = client_factory(token, args.timeout) if kind.calls_api else None
    try:
        report = run_validation(kind=kind, org=org, repo=args.repo, client=client)
        render_report(report)
        return report.exit_code
    finally:
        _close(client)


class _Parser(argparse.ArgumentParser):
    """Argument errors never echo the values the user passed."""

    def error(self, message: str) -> NoReturn:
        """Print a usage error and exit 2."""
        if message.startswith("unrecognized arguments:"):
            message = "unrecognized arguments."
        self.print_usage(sys.stderr)
        print(f"{self.prog}: error: {message}", file=sys.stderr)
        self.exit(2)


def _parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog=PROGRAM_NAME,
        description="Report what a GitHub token is allowed to do.",
    )
    parser.add_argument(
        "-V", "--version", action="version", version=PROGRAM_VERSION_STRING
    )
    parser.add_argument("-t", "--token", default=None)
    parser.add_argument("-T", "--timeout", type=_positive_int, default=DEFAULT_TIMEOUT)
    parser.add_argument(
        "--org",
        default=None,
        help=(
            "Organisation to check. Required for fine-grained, installation, "
            "and unknown tokens unless --repo is set"
        ),
    )
    parser.add_argument(
        "--repo",
        type=_repo,
        default=None,
        help=(
            "Repository to check as OWNER/NAME. Required for fine-grained, "
            "installation, and unknown tokens unless --org is set"
        ),
    )
    return parser


def _positive_int(value: str) -> int:
    if not value.isdigit() or int(value) <= 0:
        raise argparse.ArgumentTypeError("--timeout must be an integer greater than 0.")
    return int(value)


def _single_name(value: str) -> bool:
    return "/" not in value and not any(character.isspace() for character in value)


def _repo(value: str) -> tuple[str, str]:
    owner, separator, name = value.partition("/")
    invalid = separator != "/" or "/" in name or owner == "" or name == ""
    if invalid or any(character.isspace() for character in owner + name):
        raise argparse.ArgumentTypeError("--repo must be OWNER/NAME.")
    return owner, name


def _close(client: GitHubClient | None) -> None:
    close = getattr(client, "close", None)
    if callable(close):
        close()


def _token(flag: str | None, environ: Mapping[str, str]) -> str | None:
    raw = flag if flag is not None else environ.get("GITHUB_TOKEN")
    if raw is None:
        return None
    token = raw.strip()
    if token == "":
        return None
    return token
